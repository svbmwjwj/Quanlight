from pathlib import Path

import pytest

from quanlight.v2fly import V2flyError, expand, foreign_domains, import_direct

DATA = Path(__file__).parent / "fixtures" / "v2fly"


def values(entries):
    return sorted(e.value for e in entries)


def test_expand_include_with_attr_filter():
    assert values(expand(DATA, "only-cn")) == ["sub-cn.com"]
    assert values(expand(DATA, "no-cn")) == ["sub.com"]


def test_expand_exclude():
    with_yt = values(expand(DATA, "svc"))
    without_yt = values(expand(DATA, "svc", exclude=["youtube"]))
    assert "youtube.com" in with_yt
    assert "youtube.com" not in without_yt
    assert "sub.com" in without_yt


def test_expand_records_attrs_and_ignores_affiliation():
    by_value = {e.value: e for e in expand(DATA, "svc")}
    assert by_value["dl.svc.com"].kind == "full"
    assert by_value["dl.svc.com"].attrs == frozenset({"cn"})
    assert by_value["tracked.svc.com"].attrs == frozenset()
    assert by_value["sub.com"].file == "svc-sub"


def test_expand_cycle_and_missing():
    with pytest.raises(V2flyError, match="loop-a"):
        expand(DATA, "loop-a")
    with pytest.raises(V2flyError, match="does-not-exist"):
        expand(DATA, "broken")


def test_expand_filter_applies_to_nested_includes():
    assert values(expand(DATA, "nest-top")) == ["leafcn.com", "midcn.com"]


def test_import_direct_mapping():
    result = import_direct(expand(DATA, "geolocation-cn"), source="v2fly:geolocation-cn")
    got = [(r.type, r.value) for r in result.rules]
    assert got == [
        ("host-suffix", "cn"),
        ("host-suffix", "example.cn"),
        ("host-suffix", "alt.example.cn"),
        ("host", "api.example-cdn.com"),
        ("host-suffix", "svc.com"),
        ("host-suffix", "alt-svc.com"),
        ("host", "api.svc-cdn.net"),
        ("host-suffix", "cn.svc.com"),
        ("host", "dl.svc.com"),
        ("host-suffix", "tracked.svc.com"),
        ("host-suffix", "sub.com"),
        ("host-suffix", "sub-cn.com"),
        ("host-suffix", "youtube.com"),
    ]
    assert all(r.source == "v2fly:geolocation-cn" for r in result.rules)
    skipped = {(e.value, reason) for e, reason in result.skipped}
    assert ("overseas.example.cn", "not-cn") in skipped
    assert ("ads.example.cn", "ads") in skipped
    assert ("cnkw", "keyword") in skipped
    assert (r"^x\.example\.cn$", "regexp") in skipped
    assert ("svckw", "keyword") in skipped


def test_import_direct_rejects_unknown_kind(tmp_path):
    (tmp_path / "f").write_text("weird:example.com\n")
    with pytest.raises(V2flyError, match="weird"):
        import_direct(expand(tmp_path, "f"), source="x")


def test_foreign_domains_drop_cn_and_patterns():
    domains = foreign_domains(expand(DATA, "geolocation-!cn"))
    assert domains == ["google.com", "www.google.cn", "t.me", "example.cn"]
