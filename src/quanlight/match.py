"""Single-rule matching and ordered routing that models Quantumult X.

The routing model (host rules of every list first, then IP rules, then the
final policy) is provisional until the on-device probe confirms it.
"""

import ipaddress
from collections.abc import Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase

from .model import Rule, normalize_host

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


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


def route(lists: Sequence[RuleList], host: str | None, ip: IPAddress | None, final: str) -> str:
    if host is not None:
        for rule_list in lists:
            if any(rule_matches_host(rule, host) for rule in rule_list.rules):
                return rule_list.policy
    if ip is not None:
        for rule_list in lists:
            if any(rule_matches_ip(rule, ip) for rule in rule_list.rules):
                return rule_list.policy
    return final
