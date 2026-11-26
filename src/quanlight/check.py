"""Direct exceptions, mis-routing (misfire) detection and cross-bundle checks."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from fnmatch import fnmatchcase
import ipaddress

from .match import IPNetwork, RuleList, networks_overlap, rule_matches_host
from .model import HOST_TYPES, Bundle, Rule


def proxy_rules(bundle: Bundle) -> list[Rule]:
    return [rule for rule in bundle.rules if rule.role != "cn-exception"]


def direct_exceptions(bundles: Sequence[Bundle]) -> list[Rule]:
    """cn-exception rules whose value some proxy host rule would otherwise capture."""
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
    """Host rules of one list, indexed so lookups cost O(labels), not O(rules)."""

    def __init__(self, rules: Iterable[Rule]):
        self.exact: dict[str, Rule] = {}
        self.suffix: dict[str, Rule] = {}
        self.patterns: list[Rule] = []
        for rule in rules:
            if rule.type == "host":
                self.exact.setdefault(rule.value, rule)
            elif rule.type == "host-suffix":
                self.suffix.setdefault(rule.value, rule)
            elif rule.type in ("host-wildcard", "host-keyword"):
                self.patterns.append(rule)

    def match(self, host: str) -> Rule | None:
        if host in self.exact:
            return self.exact[host]
        labels = host.split(".")
        for i in range(len(labels)):
            if (rule := self.suffix.get(".".join(labels[i:]))) is not None:
                return rule
        for rule in self.patterns:
            hit = fnmatchcase(host, rule.value) if rule.type == "host-wildcard" else rule.value in host
            if hit:
                return rule
        return None


def _first_match(indexed: list[tuple[RuleList, _HostIndex]], host: str) -> tuple[RuleList, Rule] | None:
    for rule_list, index in indexed:
        if (rule := index.match(host)) is not None:
            return rule_list, rule
    return None


def _parent_in(host: str, domains: set[str]) -> str | None:
    labels = host.split(".")
    for i in range(len(labels)):
        candidate = ".".join(labels[i:])
        if candidate in domains:
            return candidate
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

    # A mainland domain (and everything under it) must route direct.
    for domain in domains:
        if (hit := _first_match(indexed, domain)) is not None:
            record(hit[0], hit[1], domain)
    # A proxy rule must not target a host that lies under a mainland domain.
    for rule_list, _ in indexed:
        for rule in rule_list.rules:
            if rule.type in ("host", "host-suffix") and (parent := _parent_in(rule.value, domains)):
                hit = _first_match(indexed, rule.value)
                if hit is not None and hit[0].policy != "direct":
                    record(rule_list, rule, parent)
    # Proxy networks must not overlap mainland networks.
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
    rank = {b.name: i for i, b in enumerate(ordered)}
    owners: dict[tuple[str, str], str] = {}
    for bundle in ordered:
        for rule in proxy_rules(bundle):
            key = (rule.type, rule.value)
            if key in owners and owners[key] != bundle.name:
                errors.append(f"duplicate rule {rule.type}, {rule.value} in {owners[key]} and {bundle.name}")
            owners.setdefault(key, bundle.name)
    for broad in ordered:
        for narrow in ordered:
            if broad.name == narrow.name or rank[broad.name] > rank[narrow.name]:
                continue
            for n_rule in proxy_rules(narrow):
                if n_rule.type not in ("host", "host-suffix"):
                    continue
                for b_rule in proxy_rules(broad):
                    if (b_rule.type, b_rule.value) != (n_rule.type, n_rule.value) and rule_matches_host(
                        b_rule, n_rule.value
                    ):
                        errors.append(
                            f"{broad.name} ({b_rule.type}, {b_rule.value}) covers "
                            f"{narrow.name} ({n_rule.type}, {n_rule.value}); order {narrow.name} first"
                        )
    return errors


def overdue_broad(bundles: Sequence[Bundle], today: date) -> list[Rule]:
    return [
        rule
        for bundle in bundles
        for rule in bundle.rules
        if rule.breadth == "broad" and rule.review_by is not None and rule.review_by < today
    ]
