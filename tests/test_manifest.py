from pathlib import Path

import pytest

from quanlight.manifest import ManifestError, check_bundle_files, load_bundle, validate_bundle
from quanlight.model import Bundle, Note, Rule, UpstreamSpec

HEAD = 'name = "svc"\ndescription = "d"\norder = 1\n'


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "svc.toml"
    path.write_text(body, encoding="utf-8")
    return path


def bundle_with(*rules: Rule, **kw) -> Bundle:
    return Bundle(name="svc", description="test", order=10, rules=tuple(rules), **kw)


def rule(type_: str, value: str, source: str = "manual", reason: str | None = "r") -> Rule:
    return Rule(type=type_, value=value, source=source, reason=reason)


def test_load_full_manifest(tmp_path):
    path = write(
        tmp_path,
        HEAD + '[[upstream]]\nkind = "v2fly"\nfile = "tencent"\napps = "WeChat, QQ"\nskip_includes = ["webnovel"]\n'
        '[[upstream]]\nkind = "dnsmasq-apple-china"\n'
        '[[rule]]\ntype = "host-suffix"\nvalue = "Example.CN."\nsource = "manual"\nreason = "r"\n'
        '[[exclude]]\nvalue = "Blocked.com"\nreason = "overseas"\n'
        '[[keep]]\nvalue = "1.0.1.0/24"\nreason = "mainland"\n',
    )
    bundle = load_bundle(path)
    assert bundle.rules == (Rule("host-suffix", "example.cn", "manual", "r"),)
    assert bundle.upstream == (UpstreamSpec("v2fly", "tencent", "WeChat, QQ", ("webnovel",)), UpstreamSpec("dnsmasq-apple-china"))
    assert [u.key for u in bundle.upstream] == ["v2fly:tencent", "dnsmasq-apple-china"]
    assert bundle.exclude == (Note("blocked.com", "overseas"),)
    assert bundle.keep == (Note("1.0.1.0/24", "mainland"),)
    assert validate_bundle(bundle) == []


@pytest.mark.parametrize(
    "body",
    [
        HEAD + 'uses = ["x"]\n',
        HEAD + '[[rule]]\ntype = "host"\nvalue = "a.com"\nsource = "manual"\nrole = "core"\n',
        HEAD + '[[rule]]\ntype = "host"\nvalue = "a.com"\nsource = "manual"\nbreadth = "broad"\n',
        HEAD + '[[keep]]\nvalue = "a.com"\nreason = "r"\nexempt = ["b.com"]\n',
    ],
)
def test_load_rejects_retired_keys(tmp_path, body):
    with pytest.raises(ManifestError):
        load_bundle(write(tmp_path, body))


def test_validate_rejects_unknown_type_and_upstream():
    assert any("ip-asn" in e for e in validate_bundle(bundle_with(rule("ip-asn", "13335"))))
    assert any("nope" in e for e in validate_bundle(bundle_with(upstream=(UpstreamSpec("nope"),))))


def test_validate_upstream_fields():
    def errs(*specs):
        return validate_bundle(bundle_with(upstream=specs))

    assert any("file and apps" in e for e in errs(UpstreamSpec("v2fly", "tencent")))
    assert any("takes no file" in e for e in errs(UpstreamSpec("china-operator-ip", "x")))
    assert any("takes no file" in e for e in errs(UpstreamSpec("china-operator-ip", skip_includes=("x",))))
    assert any("duplicate" in e for e in errs(UpstreamSpec("v2fly", "jd", "JD"), UpstreamSpec("v2fly", "jd", "JD")))
    assert errs(UpstreamSpec("v2fly", "jd", "JD"), UpstreamSpec("china-operator-ip")) == []


def test_validate_reason_rules():
    assert any("reason" in e for e in validate_bundle(bundle_with(rule("host", "a.com", reason=None))))
    assert any("reason" in e for e in validate_bundle(bundle_with(rule("host", "a.com", "observed", None))))
    official = rule("host", "a.com", "official:https://example.com/doc", None)
    assert validate_bundle(bundle_with(official)) == []
    assert any("reason" in e for e in validate_bundle(bundle_with(rule("host-keyword", "x", "official:https://e.com", None))))
    assert any("source" in e for e in validate_bundle(bundle_with(rule("host", "a.com", "v2fly:x"))))


def test_validate_notes_need_reason():
    assert validate_bundle(bundle_with(exclude=(Note("a.com", ""),)))
    assert validate_bundle(bundle_with(keep=(Note("", "r"),)))


def test_validate_rejects_bad_values():
    bad = [
        rule("ip-cidr", "2001:db8::/32"),
        rule("ip6-cidr", "10.0.0.0/8"),
        rule("ip-cidr", "not-a-network"),
        rule("host-suffix", "bad host.com"),
        rule("host-suffix", "*.example.com"),
    ]
    for r in bad:
        assert validate_bundle(bundle_with(r)), r


def test_validate_rejects_bad_and_reserved_names():
    for name in ("direct", "final", "Bad Name", "a/b", "x,y"):
        assert validate_bundle(Bundle(name=name, description="d", order=1, rules=())), name


def test_check_bundle_files_requires_name_to_match_file(tmp_path):
    (tmp_path / "china.toml").write_text('name = "other"\ndescription = "d"\norder = 1\n')
    assert any("china.toml" in e for e in check_bundle_files(tmp_path))
