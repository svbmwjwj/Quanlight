from datetime import date
from pathlib import Path

from quanlight.manifest import dump_bundle, load_bundle, validate_bundle
from quanlight.model import Bundle, Rule

TODAY = date(2026, 11, 26)


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "svc.toml"
    path.write_text(body, encoding="utf-8")
    return path


def bundle_with(*rules: Rule) -> Bundle:
    return Bundle(name="svc", description="test", order=10, rules=tuple(rules))


def rule(type_: str, value: str, **kw) -> Rule:
    return Rule(type=type_, value=value, role=kw.pop("role", "core"), source=kw.pop("source", "manual"), **kw)


def test_load_normalizes_host(tmp_path):
    path = write(
        tmp_path,
        'name = "svc"\ndescription = "d"\norder = 1\n'
        '[[rule]]\ntype = "host-suffix"\nvalue = "Telegram.ORG."\nrole = "core"\nsource = "manual"\n'
        '[[upstream]]\nkind = "telegram-cidr"\n',
    )
    bundle = load_bundle(path)
    assert bundle.rules[0].value == "telegram.org"
    assert bundle.upstream == ("telegram-cidr",)


def test_validate_rejects_unknown_type():
    errors = validate_bundle(bundle_with(rule("user-agent", "Telegram*")), TODAY)
    assert any("user-agent" in e for e in errors)


def test_validate_requires_reason():
    rules = [
        rule("host-keyword", "sift"),
        rule("ip-asn", "399358", asn_verified="bgp.tools 2026-11-26"),
        rule("host-suffix", "sentry.io", breadth="broad", review_by=date(2027, 1, 1)),
        rule("host-suffix", "example.cn", exempt=("a.example.cn",)),
    ]
    for r in rules:
        errors = validate_bundle(bundle_with(r), TODAY)
        assert any("reason" in e for e in errors), r


def test_validate_broad_requires_review_by():
    missing = rule("host-suffix", "sentry.io", breadth="broad", reason="r")
    assert any("review_by" in e for e in validate_bundle(bundle_with(missing), TODAY))
    expired = rule("host-suffix", "sentry.io", breadth="broad", reason="r", review_by=date(2026, 1, 1))
    assert any("review_by" in e for e in validate_bundle(bundle_with(expired), TODAY))
    ok = rule("host-suffix", "sentry.io", breadth="broad", reason="r", review_by=date(2027, 1, 1))
    assert validate_bundle(bundle_with(ok), TODAY) == []


def test_validate_asn_requires_verification():
    r = rule("ip-asn", "399358", reason="Anthropic only")
    assert any("asn_verified" in e for e in validate_bundle(bundle_with(r), TODAY))


def test_validate_rejects_bad_values():
    bad = [
        rule("ip-cidr", "2001:db8::/32"),
        rule("ip6-cidr", "10.0.0.0/8"),
        rule("ip-cidr", "not-a-network"),
        rule("host-suffix", "bad host.com"),
        rule("host-suffix", "*.example.com"),
        rule("ip-asn", "AS123", reason="r", asn_verified="x"),
    ]
    for r in bad:
        assert validate_bundle(bundle_with(r), TODAY), r


def test_validate_rejects_unknown_role():
    assert validate_bundle(bundle_with(rule("host", "a.example.com", role="other")), TODAY)


def test_dump_roundtrip(tmp_path):
    original = Bundle(
        name="svc",
        description='quote " and backslash \\',
        order=20,
        rules=(
            rule("host-suffix", "example.com", source="v2fly:svc"),
            rule(
                "host-suffix",
                "sentry.io",
                role="dependency",
                breadth="broad",
                reason="not observed yet",
                review_by=date(2027, 2, 28),
                exempt=("a.sentry.io",),
            ),
            rule("ip-asn", "399358", reason="r", asn_verified="bgp.tools 2026-11-26"),
        ),
        upstream=("telegram-cidr",),
        uses=("shared-persona",),
        v2fly_exclude=("youtube",),
    )
    path = write(tmp_path, dump_bundle(original))
    assert load_bundle(path) == original


def test_validate_rejects_bad_and_reserved_names():
    for name in ("direct", "direct-exceptions", "Bad Name", "a/b", "x,y"):
        bundle = Bundle(name=name, description="d", order=1, rules=())
        assert validate_bundle(bundle, TODAY), name


def test_check_bundle_files_requires_name_to_match_file(tmp_path):
    from quanlight.manifest import check_bundle_files

    (tmp_path / "telegram.toml").write_text('name = "other"\ndescription = "d"\norder = 1\n')
    errors = check_bundle_files(tmp_path)
    assert any("telegram.toml" in e for e in errors)
