from datetime import date
from ipaddress import ip_network
from pathlib import Path

from quanlight.cli import CheckData, build
from quanlight.manifest import dump_bundle
from quanlight.model import Bundle, Rule

TODAY = date(2026, 11, 26)
FIX = Path(__file__).parent / "fixtures"
TG_CIDR = (FIX / "telegram-cidr.txt").read_text()


def r(type_, value, role="core"):
    return Rule(type=type_, value=value, role=role, source="manual")


def setup(tmp_path: Path, extra_rule: Rule | None = None, samples: str | None = None) -> dict:
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir()
    tg_rules = (r("host-suffix", "telegram.org"), r("host", "t.me")) + ((extra_rule,) if extra_rule else ())
    (bundles_dir / "telegram.toml").write_text(
        dump_bundle(Bundle("telegram", "Telegram", 40, tg_rules, upstream=("telegram-cidr",)))
    )
    (bundles_dir / "apns.toml").write_text(dump_bundle(Bundle("apns", "APNs", 10, (r("host-suffix", "push.apple.com"),))))
    samples_path = tmp_path / "samples.toml"
    samples_path.write_text(
        samples
        or '[[sample]]\nhost = "courier.push.apple.com"\nexpect = "apns"\n'
        '[[sample]]\nhost = "www.taobao.com"\nexpect = "direct"\n'
        '[[sample]]\nip = "91.108.56.1"\nexpect = "telegram"\n'
    )
    data = CheckData(
        cn_domains={"taobao.com", "qq.com"},
        cn_networks=[ip_network("1.0.1.0/24")],
        provenance={"dnsmasq-china-list": "abc123"},
    )
    return dict(
        bundles_dir=bundles_dir,
        out_dir=tmp_path / "dist",
        today=TODAY,
        data=data,
        upstream={"telegram-cidr": TG_CIDR},
        samples=samples_path,
        base_url="https://cdn.example/q@release",
        static_files=(),
    )


def test_build_writes_lists(tmp_path):
    args = setup(tmp_path)
    report = build(**args)
    assert report.errors == []
    out = args["out_dir"]
    assert (out / "ios" / "apns.list").is_file()
    assert (out / "ios" / "direct-exceptions.list").is_file()
    telegram = (out / "ios" / "telegram.list").read_text()
    assert "ip-cidr, 91.108.56.0/22, telegram" in telegram
    assert "ip6-cidr, 2001:b28:f23d::/48, telegram" in telegram
    assert "/ios/telegram.list" in (out / "README.md").read_text()
    assert report.counts["telegram"] == 5


def test_build_fails_without_writing(tmp_path):
    args = setup(tmp_path, extra_rule=r("host-suffix", "qq.com"))
    report = build(**args)
    assert any("qq.com" in e for e in report.errors)
    assert not args["out_dir"].exists()


def test_samples_mismatch_fails(tmp_path):
    args = setup(tmp_path, samples='[[sample]]\nhost = "web.telegram.org"\nexpect = "direct"\n')
    report = build(**args)
    assert any("web.telegram.org" in e for e in report.errors)
    assert not args["out_dir"].exists()


def test_upstream_empty_fails(tmp_path):
    args = setup(tmp_path)
    args["upstream"] = {"telegram-cidr": ""}
    report = build(**args)
    assert any("telegram-cidr" in e for e in report.errors)
    assert not args["out_dir"].exists()


def test_report_markdown_lists_errors(tmp_path):
    args = setup(tmp_path, extra_rule=r("host-suffix", "qq.com"))
    assert "qq.com" in build(**args).to_markdown()


def test_diff_v2fly_reports_changes(tmp_path, capsys):
    from quanlight.cli import main

    bundles = tmp_path / "bundles"
    bundles.mkdir()
    rules = (
        Rule("host-suffix", "sub.com", "core", "v2fly:svc-sub"),
        Rule("host-suffix", "gone.com", "core", "v2fly:svc-sub"),
    )
    (bundles / "svc.toml").write_text(dump_bundle(Bundle("svc", "d", 10, rules)))
    code = main(["diff-v2fly", "--bundles", str(bundles), "--v2fly-data", str(FIX / "v2fly")])
    out = capsys.readouterr().out
    assert code == 0
    assert "| svc | added | host-suffix, sub-cn.com |" in out
    assert "| svc | removed | host-suffix, gone.com |" in out
