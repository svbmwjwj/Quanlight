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
    assert route([first, second], "www.example.com", None, final="direct") == "policy-b"
    assert route([first, second], "api.example.com", None, final="direct") == "policy-a"
    assert route([first, second], "other.net", ip_address("10.1.2.3"), final="direct") == "policy-b"
    assert route([first, second], "other.net", ip_address("8.8.8.8"), final="direct") == "direct"
    assert route([first, second], None, None, final="direct") == "direct"


# 以下用例对应 D-019 真机探针的结果。


def test_route_host_in_later_list_beats_suffix_in_earlier_list():
    earlier = RuleList("reject", "reject", (r("host-suffix", "example.org"),))
    later = RuleList("direct", "direct", (r("host", "www.example.org"),))
    assert route([earlier, later], "www.example.org", None, final="proxy") == "direct"


def test_route_same_type_earlier_list_wins():
    earlier = RuleList("reject", "reject", (r("host-suffix", "example.com"),))
    later = RuleList("direct", "direct", (r("host-suffix", "example.com"),))
    assert route([earlier, later], "www.example.com", None, final="proxy") == "reject"


def test_route_wildcard_does_not_match_bare_domain():
    lists = [RuleList("reject", "reject", (r("host-wildcard", "*.iana.org"),))]
    assert route(lists, "www.iana.org", None, final="direct") == "reject"
    assert route(lists, "iana.org", None, final="direct") == "direct"


def test_route_provisional_suffix_wildcard_keyword_order():
    keyword = RuleList("k", "k", (r("host-keyword", "example"),))
    wildcard = RuleList("w", "w", (r("host-wildcard", "*.example.net"),))
    suffix = RuleList("s", "s", (r("host-suffix", "example.net"),))
    assert route([keyword, wildcard, suffix], "a.example.net", None, final="direct") == "s"
    assert route([keyword, wildcard], "a.example.net", None, final="direct") == "w"
