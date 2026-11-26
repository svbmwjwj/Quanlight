"""反向误伤检查：境外域名与网段不得落到直连；APNs 不得被直连规则遮住。"""

import ipaddress
from bisect import bisect_right
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .match import IPNetwork, Router, rule_matches_host
from .model import Rule

DIRECT = "direct"


@dataclass(frozen=True)
class Hit:
    dataset: str  # 命中的检查数据集
    target: str  # 境外域名或网段
    rule: Rule  # 把它送到直连的规则


def domain_hits(router: Router, datasets: Mapping[str, Iterable[str]]) -> list[Hit]:
    """按模拟器逐个路由境外域名，落到直连列表即为命中。"""
    hits: list[Hit] = []
    for dataset, domains in datasets.items():
        for domain in domains:
            if (hit := router.match_host(domain)) is not None and hit[0].policy == DIRECT:
                hits.append(Hit(dataset, domain, hit[1]))
    return hits


def network_hits(direct_rules: Iterable[Rule], datasets: Mapping[str, Iterable[IPNetwork]]) -> list[Hit]:
    """直连网段与境外网段有任何重叠即为命中。"""
    by_version: dict[int, list[tuple[int, int, Rule]]] = {4: [], 6: []}
    for rule in direct_rules:
        if rule.type in ("ip-cidr", "ip6-cidr"):
            net = ipaddress.ip_network(rule.value)
            by_version[net.version].append((int(net.network_address), int(net.broadcast_address), rule))
    tables = {}
    for version, spans in by_version.items():
        spans.sort(key=lambda s: s[0])
        # 前缀最大结束地址：向前扫描时据此提前停止，网段彼此重叠时也成立
        reach, running = [], -1
        for _, end, _ in spans:
            running = max(running, end)
            reach.append(running)
        tables[version] = ([s[0] for s in spans], reach, spans)
    hits: list[Hit] = []
    for dataset, nets in datasets.items():
        for net in nets:
            starts, reach, spans = tables[net.version]
            lo, hi = int(net.network_address), int(net.broadcast_address)
            j = bisect_right(starts, hi) - 1
            found = []
            while j >= 0 and reach[j] >= lo:
                if spans[j][1] >= lo:
                    found.append(spans[j][2])
                j -= 1
            hits += [Hit(dataset, str(net), rule) for rule in reversed(found)]
    return hits


def shadowed(router: Router, protected: str) -> list[tuple[Rule, Rule]]:
    """直连列表中落在受保护列表（APNs）域名之下、且模拟时先于它命中的规则。"""
    lists = {lst.name: lst for lst in router.lists}
    zones = [r for r in lists[protected].rules if r.type in ("host", "host-suffix")]
    found: list[tuple[Rule, Rule]] = []
    for lst in router.lists:
        if lst.policy != DIRECT:
            continue
        for rule in lst.rules:
            if rule.type not in ("host", "host-suffix"):
                continue
            for zone in zones:
                if rule_matches_host(zone, rule.value):
                    hit = router.match_host(rule.value)
                    if hit is not None and hit[0].policy == DIRECT:
                        found.append((rule, zone))
    return found
