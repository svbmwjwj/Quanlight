from pathlib import Path

import pytest

from quanlight.model import Bundle, Rule
from quanlight.v2fly import V2flyError, diff, expand, to_rules

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


def test_to_rules_mapping():
    result = to_rules(expand(DATA, "svc", exclude=["youtube"]), source="v2fly:svc")
    got = {(r.type, r.value, r.role) for r in result.rules}
    assert ("host-suffix", "svc.com", "core") in got
    assert ("host-suffix", "alt-svc.com", "core") in got
    assert ("host", "api.svc-cdn.net", "core") in got
    assert ("host-suffix", "cn.svc.com", "cn-exception") in got
    assert ("host", "dl.svc.com", "cn-exception") in got
    assert all(r.source == "v2fly:svc" for r in result.rules)
    skipped = {(e.value, reason) for e, reason in result.skipped}
    assert ("svckw", "keyword-needs-review") in skipped
    assert (r"^x\.svc\.com$", "regexp-unsupported") in skipped
    assert ("ads.svc.com", "ads") in skipped
    assert not any(r.value == "ads.svc.com" for r in result.rules)


def test_diff():
    imported = to_rules(expand(DATA, "svc-sub"), source="v2fly:svc-sub")
    bundle = Bundle(
        name="svc",
        description="d",
        order=1,
        rules=(
            Rule("host-suffix", "sub.com", "core", "v2fly:svc-sub"),
            Rule("host-suffix", "gone.com", "core", "v2fly:svc-sub"),
            Rule("host", "manual.example.com", "core", "manual"),
        ),
    )
    added, removed = diff(bundle, imported)
    assert [(r.type, r.value) for r in added] == [("host-suffix", "sub-cn.com")]
    assert [(r.type, r.value) for r in removed] == [("host-suffix", "gone.com")]
