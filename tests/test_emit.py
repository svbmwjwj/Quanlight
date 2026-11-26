from datetime import date

from quanlight.emit import mirror_bases, render_filter_remote, render_list, render_release_readme
from quanlight.model import Rule


def r(type_, value):
    return Rule(type=type_, value=value, source="manual")


RULES = [r("ip-cidr", "1.0.1.0/24"), r("host-suffix", "qq.com"), r("host", "a.qq.com"), r("host", "a.qq.com")]
HEADER = ["# upstream dnsmasq-china-list: abc (entries: 2)"]


def test_render_list_deterministic():
    first = render_list("china", RULES, HEADER)
    assert first == render_list("china", RULES, HEADER)
    assert date.today().isoformat() not in first
    assert first.endswith("\n")
    assert first.splitlines()[:3] == ["# quanlight china", "# rules: 3", HEADER[0]]


def test_render_list_order_and_dedupe():
    body = [l for l in render_list("china", RULES, HEADER).splitlines() if not l.startswith("#")]
    assert body == ["host, a.qq.com, china", "host-suffix, qq.com, china", "ip-cidr, 1.0.1.0/24, china"]


def test_render_filter_remote():
    lines = render_filter_remote(["apns", "china"], {"china"}, "https://cdn.example/q@release").splitlines()
    assert lines[0].startswith("https://cdn.example/q@release/apns.list, tag=quanlight-apns, force-policy=<proxy-policy>,")
    assert lines[1].startswith("https://cdn.example/q@release/china.list, tag=quanlight-china, force-policy=direct,")
    assert all("update-interval=-1," in l for l in lines[:2])
    assert lines[-1].startswith("FILTER_LAN,")


def test_mirror_bases_cover_github_and_mainland():
    bases = mirror_bases("owner", "quanlight")
    assert bases["github"] == "https://raw.githubusercontent.com/owner/quanlight/release"
    assert bases["ghfast"] == "https://ghfast.top/https://raw.githubusercontent.com/owner/quanlight/release"
    assert bases["jsdelivr-fastly"] == "https://fastly.jsdelivr.net/gh/owner/quanlight@release"
    assert bases["jsdelivr"] == "https://cdn.jsdelivr.net/gh/owner/quanlight@release"


def test_render_release_readme_has_both_snippets():
    text = render_release_readme(["apns", "china"], {"china"}, "owner", "quanlight")
    assert "https://raw.githubusercontent.com/owner/quanlight/release/china.list" in text
    assert "https://ghfast.top/https://raw.githubusercontent.com/owner/quanlight/release/apns.list" in text
    assert text.count("[filter_remote]") == 2
    assert text.count("final, <proxy-policy>") == 2
