from ipaddress import ip_network

from quanlight.check import domain_hits, network_hits, shadowed
from quanlight.match import Router, RuleList
from quanlight.model import Rule


def r(type_, value):
    return Rule(type=type_, value=value, source="manual")


APNS = RuleList("apns", "apns", (r("host-suffix", "push.apple.com"),))


def test_domain_hits_follow_simulator():
    china = RuleList("china", "direct", (r("host-suffix", "cn"), r("host", "www.google.cn"), r("host-suffix", "push.apple.com")))
    router = Router([APNS, china])
    hits = domain_hits(router, {"v2fly": ["google.com", "www.google.cn", "a.example.cn", "courier.push.apple.com"]})
    assert [(h.target, h.rule.value) for h in hits] == [("www.google.cn", "www.google.cn"), ("a.example.cn", "cn")]


def test_domain_hits_ignore_parent_only_coverage():
    # 直连的是境外域名的子域，不算覆盖境外域名本身
    router = Router([RuleList("china", "direct", (r("host-suffix", "dl.google.com"),))])
    assert domain_hits(router, {"v2fly": ["google.com"]}) == []


def test_network_hits_overlap_both_directions_and_versions():
    rules = [r("ip-cidr", "1.0.0.0/16"), r("ip-cidr", "8.8.4.0/24"), r("ip-cidr", "10.0.0.0/8"), r("ip6-cidr", "2400::/12")]
    datasets = {
        "google": [ip_network("8.8.0.0/16"), ip_network("2001:4860::/32")],
        "tg": [ip_network("10.1.2.0/24"), ip_network("1.1.0.0/16")],
        "v6": [ip_network("2400:1::/32")],
    }
    hits = network_hits(rules, datasets)
    assert [(h.dataset, h.target, h.rule.value) for h in hits] == [
        ("google", "8.8.0.0/16", "8.8.4.0/24"),
        ("tg", "10.1.2.0/24", "10.0.0.0/8"),
        ("v6", "2400:1::/32", "2400::/12"),
    ]


def test_network_hits_with_nested_direct_ranges():
    rules = [r("ip-cidr", "10.0.0.0/8"), r("ip-cidr", "10.5.0.0/16"), r("ip-cidr", "10.200.0.0/16")]
    hits = network_hits(rules, {"x": [ip_network("10.100.0.0/16")]})
    assert [h.rule.value for h in hits] == ["10.0.0.0/8"]


def test_shadowed_only_when_direct_wins():
    china = RuleList(
        "china",
        "direct",
        (r("host", "courier.push.apple.com"), r("host-suffix", "x.push.apple.com"), r("host-suffix", "apple.com")),
    )
    found = shadowed(Router([APNS, china]), "apns")
    assert [(rule.type, rule.value) for rule, _ in found] == [("host", "courier.push.apple.com")]
