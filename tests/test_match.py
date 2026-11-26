from ipaddress import ip_address, ip_network

from quanlight.match import RuleList, networks_overlap, route, rule_matches_host, rule_matches_ip
from quanlight.model import Rule


def r(type_: str, value: str) -> Rule:
    return Rule(type=type_, value=value, role="core", source="manual")


def test_suffix_boundary():
    rule = r("host-suffix", "telegram.org")
    assert rule_matches_host(rule, "telegram.org")
    assert rule_matches_host(rule, "web.telegram.org")
    assert not rule_matches_host(rule, "nottelegram.org")


def test_host_exact():
    assert rule_matches_host(r("host", "a.example.com"), "a.example.com")
    assert not rule_matches_host(r("host", "a.example.com"), "b.a.example.com")


def test_wildcard():
    rule = r("host-wildcard", "*.ingest.sentry.io")
    assert rule_matches_host(rule, "o1.ingest.sentry.io")
    assert not rule_matches_host(rule, "ingest.sentry.io")


def test_keyword_is_substring():
    assert rule_matches_host(r("host-keyword", "sift"), "cdn.sift.com")


def test_ip_rules_never_match_hosts_and_vice_versa():
    assert not rule_matches_host(r("ip-cidr", "1.0.0.0/8"), "1.2.3.4")
    assert not rule_matches_ip(r("host", "a.com"), ip_address("1.2.3.4"))
    assert not rule_matches_ip(r("ip-asn", "13335"), ip_address("1.1.1.1"))
    assert rule_matches_ip(r("ip6-cidr", "2001:db8::/32"), ip_address("2001:db8::1"))


def test_case_and_trailing_dot():
    lists = [RuleList("tg", "tg", (r("host-suffix", "telegram.org"),))]
    assert route(lists, "Web.Telegram.Org.", None, final="direct") == "tg"


def test_overlap_mixed_versions():
    assert not networks_overlap(ip_network("1.0.0.0/8"), ip_network("::/0"))
    assert networks_overlap(ip_network("1.0.0.0/8"), ip_network("1.2.0.0/16"))


def test_route_order_and_ip_fallback():
    first = RuleList("a", "policy-a", (r("host-suffix", "example.com"),))
    second = RuleList("b", "policy-b", (r("host", "www.example.com"), r("ip-cidr", "10.0.0.0/8")))
    assert route([first, second], "www.example.com", None, final="direct") == "policy-a"
    assert route([first, second], "other.net", ip_address("10.1.2.3"), final="direct") == "policy-b"
    assert route([first, second], "other.net", ip_address("8.8.8.8"), final="direct") == "direct"
    assert route([first, second], None, None, final="direct") == "direct"
