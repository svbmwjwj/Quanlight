from datetime import date
from ipaddress import ip_network

from quanlight.check import (
    build_ios_lists,
    cross_check,
    direct_exceptions,
    find_misfires,
    overdue_broad,
)
from quanlight.model import Bundle, Rule


def r(type_, value, role="core", **kw):
    return Rule(type=type_, value=value, role=role, source="manual", **kw)


def b(name, order, *rules):
    return Bundle(name=name, description=name, order=order, rules=tuple(rules))


def test_direct_exceptions_only_when_covered():
    google = b(
        "google",
        10,
        r("host-suffix", "google.com"),
        r("host-suffix", "dl.google.com", role="cn-exception"),
        r("host", "www.google.cn", role="cn-exception"),
    )
    exceptions = direct_exceptions([google])
    assert [(x.type, x.value) for x in exceptions] == [("host-suffix", "dl.google.com")]


def test_build_ios_lists_order():
    lists = build_ios_lists([b("z", 30, r("host", "z.com")), b("a", 10, r("host", "a.com"))], [])
    assert [(l.name, l.policy) for l in lists] == [("direct-exceptions", "direct"), ("a", "a"), ("z", "z")]


def test_misfire_domain_and_exempt():
    bad = b("svc", 10, r("host-suffix", "example.cn"))
    lists = build_ios_lists([bad], [])
    misfires = find_misfires(lists, {"a.example.cn"}, [])
    assert [(m.bundle, m.target) for m in misfires] == [("svc", "a.example.cn")]
    ok = b("svc", 10, r("host-suffix", "example.cn", exempt=("a.example.cn",), reason="r"))
    assert find_misfires(build_ios_lists([ok], []), {"a.example.cn"}, []) == []


def test_misfire_rule_under_cn_domain():
    svc = b("svc", 10, r("host", "x.qq.com"))
    misfires = find_misfires(build_ios_lists([svc], []), {"qq.com"}, [])
    assert [(m.bundle, m.target) for m in misfires] == [("svc", "qq.com")]


def test_misfire_cleared_by_exception():
    google = b("google", 10, r("host-suffix", "google.com"), r("host-suffix", "dl.google.com", role="cn-exception"))
    lists = build_ios_lists([google], direct_exceptions([google]))
    assert find_misfires(lists, {"dl.google.com", "cdn.dl.google.com"}, []) == []


def test_misfire_ip_overlap():
    svc = b("svc", 10, r("ip-cidr", "1.0.0.0/8"), r("ip6-cidr", "2001:db8::/32"))
    misfires = find_misfires(build_ios_lists([svc], []), set(), [ip_network("1.2.0.0/16"), ip_network("2400::/12")])
    assert [(m.rule.value, m.target) for m in misfires] == [("1.0.0.0/8", "1.2.0.0/16")]


def test_cross_check_duplicate_and_order():
    dup = cross_check([b("a", 10, r("host", "x.com")), b("b", 20, r("host", "x.com"))])
    assert any("x.com" in e for e in dup)
    google = b("google", 10, r("host-suffix", "googleapis.com"))
    claude = b("claude", 20, r("host", "maps.googleapis.com"))
    assert any("claude" in e and "google" in e for e in cross_check([google, claude]))
    claude_first = b("claude", 5, r("host", "maps.googleapis.com"))
    assert cross_check([google, claude_first]) == []


def test_overdue_broad():
    old = r("host-suffix", "sentry.io", breadth="broad", reason="r", review_by=date(2026, 1, 1))
    fresh = r("host-suffix", "intercom.io", breadth="broad", reason="r", review_by=date(2027, 1, 1))
    assert overdue_broad([b("c", 1, old, fresh)], date(2026, 11, 26)) == [old]


def test_misfire_wildcard_and_keyword_under_cn_domain():
    for rule in (r("host-wildcard", "*.qq.com"), r("host-keyword", ".qq.com", reason="x"), r("host-wildcard", "*.mail.qq.com")):
        misfires = find_misfires(build_ios_lists([b("svc", 10, rule)], []), {"qq.com"}, [])
        assert [(m.bundle, m.target) for m in misfires] == [("svc", "qq.com")], rule
