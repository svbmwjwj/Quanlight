"""单条规则匹配，以及模拟 Quantumult X 的路由。

路由模型按 D-019 真机探针：规则类型优先，同类型内按列表顺序，排在前面的列表先命中；
主机规则都未命中时再按列表顺序匹配 IP 规则，最后落到 final。
"""

import ipaddress
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase

from .model import Rule, normalize_host

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


# 主机规则类型的匹配优先级。host 先于 host-suffix 已由 D-019 真机探针确认；
# host-suffix、host-wildcard、host-keyword 之间的先后尚未实测，暂按社区说法排列。
HOST_TYPE_PRIORITY = ("host", "host-suffix", "host-wildcard", "host-keyword")


@dataclass(frozen=True)
class RuleList:
    name: str
    policy: str
    rules: tuple[Rule, ...]


def rule_matches_host(rule: Rule, host: str) -> bool:
    host = normalize_host(host)
    match rule.type:
        case "host":
            return host == rule.value
        case "host-suffix":
            return host == rule.value or host.endswith("." + rule.value)
        case "host-wildcard":
            return fnmatchcase(host, rule.value)
        case "host-keyword":
            return rule.value in host
    return False


def rule_matches_ip(rule: Rule, ip: IPAddress) -> bool:
    if rule.type not in ("ip-cidr", "ip6-cidr"):
        return False
    network = ipaddress.ip_network(rule.value)
    return network.version == ip.version and ip in network


def networks_overlap(a: IPNetwork, b: IPNetwork) -> bool:
    return a.version == b.version and a.overlaps(b)


class HostIndex:
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


class Router:
    """按订阅顺序排列的列表，带主机规则索引的路由模拟器。"""

    def __init__(self, lists: Sequence[RuleList]):
        self.lists = list(lists)
        self.indexed = [(lst, HostIndex(lst.rules)) for lst in self.lists]

    def match_host(self, host: str) -> tuple[RuleList, Rule] | None:
        """类型优先，同类型内按列表顺序（D-019）。"""
        host = normalize_host(host)
        for rule_type in HOST_TYPE_PRIORITY:
            for rule_list, index in self.indexed:
                if (rule := index.match(host, rule_type)) is not None:
                    return rule_list, rule
        return None

    def route(self, host: str | None, ip: IPAddress | None, final: str) -> str:
        if host is not None and (hit := self.match_host(host)) is not None:
            return hit[0].policy
        if ip is not None:
            for rule_list in self.lists:
                if any(rule_matches_ip(rule, ip) for rule in rule_list.rules):
                    return rule_list.policy
        return final


def route(lists: Sequence[RuleList], host: str | None, ip: IPAddress | None, final: str) -> str:
    return Router(lists).route(host, ip, final)
