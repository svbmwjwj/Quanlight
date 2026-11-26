from ipaddress import ip_network
from pathlib import Path

from quanlight.build import CheckData, Upstream, build, read_previous_counts
from quanlight.model import Rule

APNS = 'name = "apns"\ndescription = "d"\norder = 10\n[[rule]]\ntype = "host-suffix"\nvalue = "push.apple.com"\nsource = "manual"\nreason = "r"\n'
CHINA = (
    'name = "china"\ndescription = "d"\norder = 20\n'
    '[[upstream]]\nkind = "v2fly"\nfile = "svc"\napps = "Svc"\n'
    '[[upstream]]\nkind = "dnsmasq-apple-china"\n[[upstream]]\nkind = "china-operator-ip"\n'
)
SAMPLES = (
    '[[sample]]\nhost = "courier.push.apple.com"\nexpect = "apns"\n'
    '[[sample]]\nhost = "www.taobao.com"\nexpect = "direct"\n'
    '[[sample]]\nhost = "www.google.com"\nexpect = "final"\n'
    '[[sample]]\nip = "1.0.1.1"\nexpect = "direct"\n'
    '[[sample]]\nip = "91.108.56.1"\nexpect = "final"\n'
)


def hs(value, source="dnsmasq-apple-china"):
    return Rule("host-suffix", value, source)


def setup(tmp_path: Path, china_extra: str = "", dnsmasq=("taobao.com", "qq.com"), samples=SAMPLES) -> dict:
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir(parents=True)
    (bundles_dir / "apns.toml").write_text(APNS)
    (bundles_dir / "china.toml").write_text(CHINA + china_extra)
    samples_path = tmp_path / "samples.toml"
    samples_path.write_text(samples)
    upstream = {
        "v2fly:svc": Upstream("v2fly:svc", "v2", [Rule("host", "api.svc.cn", "v2fly:svc"), hs("tmall.com", "v2fly:svc")]),
        "dnsmasq-apple-china": Upstream("dnsmasq-apple-china", "abc", [hs(d) for d in dnsmasq]),
        "china-operator-ip": Upstream(
            "china-operator-ip",
            "def",
            [Rule("ip-cidr", "1.0.1.0/24", "china-operator-ip"), Rule("ip6-cidr", "2400::/12", "china-operator-ip")],
        ),
    }
    check = CheckData(
        domains={"v2fly geolocation-!cn": ["google.com", "t.me"]},
        networks={"telegram-cidr": [ip_network("91.108.56.0/22")]},
        provenance={"v2fly geolocation-!cn": "v2sha", "telegram-cidr": "sha256:x"},
    )
    return dict(
        bundles_dir=bundles_dir,
        out_dir=tmp_path / "dist",
        upstream=upstream,
        check=check,
        samples=samples_path,
        previous={"dnsmasq-apple-china": 3, "china-operator-ip": 2},
        owner="owner",
        repo="quanlight",
        static_files=(),
    )


def test_build_writes_lists(tmp_path):
    args = setup(tmp_path)
    report = build(**args)
    assert report.errors == []
    out = args["out_dir"]
    china = (out / "china.list").read_text()
    assert "host-suffix, taobao.com, china" in china
    assert "ip6-cidr, 2400::/12, china" in china
    assert "# upstream dnsmasq-apple-china: abc (entries: 2)" in china
    assert "host-suffix, push.apple.com, apns" in (out / "apns.list").read_text()
    readme = (out / "README.md").read_text()
    assert "https://raw.githubusercontent.com/owner/quanlight/release/china.list" in readme
    assert report.counts == {"apns": 1, "china": 6}
    assert "# upstream v2fly:svc: v2 (entries: 2)" in china
    assert report.sources["v2fly:svc"].added == 2
    assert report.sizes["china"] == (out / "china.list").stat().st_size
    assert read_previous_counts(out / "china.list") == {"v2fly:svc": 2, "dnsmasq-apple-china": 2, "china-operator-ip": 2}


def test_reverse_hit_fails_without_writing(tmp_path):
    args = setup(tmp_path, dnsmasq=("taobao.com", "google.com"))
    report = build(**args)
    assert any("reverse check" in e for e in report.errors)
    assert [(h.target, h.rule.value) for h in report.hits] == [("google.com", "google.com")]
    assert "google.com" in report.to_markdown()
    assert not args["out_dir"].exists()


def test_exclude_and_keep_clear_hits(tmp_path):
    excluded = setup(tmp_path / "a", '[[exclude]]\nvalue = "google.com"\nreason = "overseas"\n', ("taobao.com", "google.com"))
    report = build(**excluded)
    assert report.errors == []
    assert "google.com" not in (excluded["out_dir"] / "china.list").read_text()
    assert report.sources["dnsmasq-apple-china"].added == 1
    kept = setup(tmp_path / "b", '[[keep]]\nvalue = "t.me"\nreason = "checked"\n', ("taobao.com", "t.me"))
    report = build(**kept)
    assert report.errors == []
    assert [h.target for h in report.kept] == ["t.me"]
    assert "host-suffix, t.me, china" in (kept["out_dir"] / "china.list").read_text()


def test_unused_exclude_and_keep_warn(tmp_path):
    extra = '[[exclude]]\nvalue = "gone.com"\nreason = "r"\n[[keep]]\nvalue = "old.com"\nreason = "r"\n'
    report = build(**setup(tmp_path, extra))
    assert report.errors == []
    assert any("gone.com" in w for w in report.warnings) and any("old.com" in w for w in report.warnings)


def test_network_overlap_fails(tmp_path):
    args = setup(tmp_path)
    args["check"].networks["google-ipranges"] = [ip_network("1.0.0.0/16")]
    report = build(**args)
    assert [(h.target, h.rule.value) for h in report.hits] == [("1.0.0.0/16", "1.0.1.0/24")]


def test_direct_rule_under_apns_fails(tmp_path):
    extra = '[[rule]]\ntype = "host"\nvalue = "courier.push.apple.com"\nsource = "manual"\nreason = "r"\n'
    report = build(**setup(tmp_path, extra))
    assert any("courier.push.apple.com" in e and "apns" in e for e in report.errors)


def test_samples_mismatch_fails(tmp_path):
    args = setup(tmp_path, samples='[[sample]]\nhost = "www.google.com"\nexpect = "direct"\n')
    report = build(**args)
    assert any("www.google.com" in e for e in report.errors)
    assert not args["out_dir"].exists()


def test_upstream_drop_fails_and_missing_previous_warns(tmp_path):
    args = setup(tmp_path / "a")
    args["previous"] = {"dnsmasq-apple-china": 5}
    assert any("down from 5" in e for e in build(**args).errors)
    args = setup(tmp_path / "b")
    args["previous"] = None
    report = build(**args)
    assert report.errors == [] and any("drop check skipped" in w for w in report.warnings)


def test_missing_or_invalid_upstream_fails(tmp_path):
    args = setup(tmp_path / "a")
    del args["upstream"]["china-operator-ip"]
    assert any("no upstream data" in e for e in build(**args).errors)
    args = setup(tmp_path / "b", dnsmasq=("bad host.com",))
    assert any("bad host.com" in e for e in build(**args).errors)


def test_build_refuses_to_wipe_foreign_out_dir(tmp_path):
    args = setup(tmp_path)
    foreign = tmp_path / "precious"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep")
    args["out_dir"] = foreign
    assert build(**args).errors
    assert (foreign / "keep.txt").read_text() == "keep"


def test_build_replaces_its_own_previous_output(tmp_path):
    args = setup(tmp_path)
    assert build(**args).errors == []
    (args["out_dir"] / "stale.list").write_text("old")
    assert build(**args).errors == []
    assert not (args["out_dir"] / "stale.list").exists()


def test_drop_covered_keeps_routing():
    from quanlight.build import drop_covered

    rules = [hs("qq.com"), hs("a.qq.com"), hs("b.a.qq.com"), Rule("host", "c.qq.com", "x"), hs("qq.com.cn"), hs("cn")]
    kept, dropped = drop_covered(rules)
    assert [(r.type, r.value) for r in kept] == [("host-suffix", "qq.com"), ("host", "c.qq.com"), ("host-suffix", "cn")]
    assert dropped == 3


def test_build_reports_dropped_suffixes(tmp_path):
    args = setup(tmp_path, dnsmasq=("taobao.com", "www.taobao.com", "qq.com"))
    report = build(**args)
    assert report.errors == []
    assert report.redundant == {"china": 1}
    assert "www.taobao.com" not in (args["out_dir"] / "china.list").read_text()
    assert "dropped 1 host-suffix" in report.to_markdown()
