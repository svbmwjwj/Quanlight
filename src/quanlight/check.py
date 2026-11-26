"""直连例外、误伤检查与服务包之间的交叉检查。"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from fnmatch import fnmatchcase
import ipaddress

from .match import HOST_TYPE_PRIORITY, IPNetwork, RuleList, networks_overlap, route, rule_matches_host
from .model import HOST_TYPES, Bundle, Rule


def proxy_rules(bundle: Bundle) -> list[Rule]:
    return [rule for rule in bundle.rules if rule.role != "cn-exception"]


def direct_exceptions(bundles: Sequence[Bundle]) -> list[Rule]:
    """会被某条代理主机规则命中的 cn-exception 条目，需要生成直连例外。"""
    proxies = [rule for bundle in bundles for rule in proxy_rules(bundle) if rule.type in HOST_TYPES]
    found: dict[tuple[str, str], Rule] = {}
    for bundle in bundles:
        for rule in bundle.rules:
            if rule.role == "cn-exception" and any(rule_matches_host(p, rule.value) for p in proxies):
                found.setdefault((rule.type, rule.value), rule)
    return [found[key] for key in sorted(found)]


def _ordered(bundles: Sequence[Bundle]) -> list[Bundle]:
    return sorted(bundles, key=lambda b: (b.order, b.name))


def build_ios_lists(bundles: Sequence[Bundle], exceptions: list[Rule]) -> list[RuleList]:
    lists = [RuleList("direct-exceptions", "direct", tuple(exceptions))]
    lists += [RuleList(b.name, b.name, tuple(proxy_rules(b))) for b in _ordered(bundles)]
    return lists


@dataclass(frozen=True)
class Misfire:
    bundle: str
    rule: Rule
    target: str


class _HostIndex:
    """单个列表的主机规则索引，查询开销与域名层级数相关，而不是与规则数相关。"""

    def __init__(self, rules: Iterable[Rule]):
        self.exact: dict[str, Rule] = {}
        self.suffix: dict[str, Rule] = {}
        self.wildcards: list[Rule] = []
        self.keywords: list[Rule] = []
        for rule in rules:
            if rule.type == "host":
                self.exact.setdefault(rule.value, rule)
            elif rule.type == "host-suffix":
                self.suffix.setdefault(rule.value, rule)
            elif rule.type == "host-wildcard":
                self.wildcards.append(rule)
            elif rule.type == "host-keyword":
                self.keywords.append(rule)

    def match(self, host: str, rule_type: str) -> Rule | None:
        """只在指定类型的规则中查找命中。"""
        if rule_type == "host":
            return self.exact.get(host)
        if rule_type == "host-suffix":
            labels = host.split(".")
            for i in range(len(labels)):
                if (rule := self.suffix.get(".".join(labels[i:]))) is not None:
                    return rule
            return None
        if rule_type == "host-wildcard":
            return next((rule for rule in self.wildcards if fnmatchcase(host, rule.value)), None)
        if rule_type == "host-keyword":
            return next((rule for rule in self.keywords if rule.value in host), None)
        return None


def _first_match(indexed: list[tuple[RuleList, _HostIndex]], host: str) -> tuple[RuleList, Rule] | None:
    """与 match.route 相同的语义：类型优先，同类型内按列表顺序。"""
    for rule_type in HOST_TYPE_PRIORITY:
        for rule_list, index in indexed:
            if (rule := index.match(host, rule_type)) is not None:
                return rule_list, rule
    return None


def _parent_in(host: str, domains: set[str]) -> str | None:
    labels = host.split(".")
    for i in range(len(labels)):
        candidate = ".".join(labels[i:])
        if candidate in domains:
            return candidate
    return None


# 真实服务不会使用的标签，用来代表国内域名的“任意子域”。
_ANY_LABEL = "zz9-quanlight-any"


def _literal_tail(rule: Rule) -> str | None:
    """规则指向的主机部分，适用于 host、host-suffix 与 host-wildcard。"""
    if rule.type in ("host", "host-suffix"):
        return rule.value
    if rule.type == "host-wildcard":
        tail = rule.value[max(rule.value.rfind("*"), rule.value.rfind("?")) + 1 :].lstrip(".")
        return tail or None
    return None


def find_misfires(
    lists: Sequence[RuleList], cn_domains: Iterable[str], cn_networks: Iterable[IPNetwork]
) -> list[Misfire]:
    domains = set(cn_domains)
    indexed = [(lst, _HostIndex(lst.rules)) for lst in lists]
    found: dict[tuple[str, str, str, str], Misfire] = {}

    def record(rule_list: RuleList, rule: Rule, target: str) -> None:
        if rule_list.policy == "direct" or target in rule.exempt:
            return
        found.setdefault((rule_list.name, rule.type, rule.value, target), Misfire(rule_list.name, rule, target))

    # 国内域名及其子域都必须落到直连。
    for domain in domains:
        for host in (domain, f"{_ANY_LABEL}.{domain}"):
            if (hit := _first_match(indexed, host)) is not None:
                record(hit[0], hit[1], domain)
    # 代理规则不能指向国内域名之下的主机。
    for rule_list, _ in indexed:
        for rule in rule_list.rules:
            tail = _literal_tail(rule)
            if tail is None or (parent := _parent_in(tail, domains)) is None:
                continue
            probe = tail if rule.type != "host-wildcard" else f"{_ANY_LABEL}.{tail}"
            hit = _first_match(indexed, probe)
            if hit is not None and hit[0].policy != "direct":
                record(rule_list, rule, parent)
    # 代理网段不能与大陆网段重叠。
    networks = list(cn_networks)
    for rule_list in lists:
        for rule in rule_list.rules:
            if rule.type in ("ip-cidr", "ip6-cidr"):
                net = ipaddress.ip_network(rule.value)
                for cn in networks:
                    if networks_overlap(net, cn):
                        record(rule_list, rule, str(cn))
    return sorted(found.values(), key=lambda m: (m.bundle, m.rule.value, m.target))


def cross_check(bundles: Sequence[Bundle]) -> list[str]:
    errors: list[str] = []
    ordered = _ordered(bundles)
    owners: dict[tuple[str, str], str] = {}
    for bundle in ordered:
        for rule in proxy_rules(bundle):
            key = (rule.type, rule.value)
            if key in owners and owners[key] != bundle.name:
                errors.append(f"duplicate rule {rule.type}, {rule.value} in {owners[key]} and {bundle.name}")
            owners.setdefault(key, bundle.name)
    # 按 D-019 的路由模型逐条试探：每条主机规则的值都应先命中本包，否则被别的包遮住
    lists = [RuleList(b.name, b.name, tuple(proxy_rules(b))) for b in ordered]
    for bundle in ordered:
        for rule in proxy_rules(bundle):
            if rule.type not in ("host", "host-suffix", "host-wildcard"):
                continue
            if owners[(rule.type, rule.value)] != bundle.name:
                continue
            probe = rule.value.replace("*", "a").replace("?", "a")
            winner = route(lists, probe, None, final="")
            if winner != bundle.name:
                errors.append(
                    f"{winner} matches {probe} before {bundle.name} ({rule.type}, {rule.value}); "
                    "reorder bundles or narrow the rule"
                )
    return errors


def overdue_broad(bundles: Sequence[Bundle], today: date) -> list[Rule]:
    return [
        rule
        for bundle in bundles
        for rule in bundle.rules
        if rule.breadth == "broad" and rule.review_by is not None and rule.review_by < today
    ]
