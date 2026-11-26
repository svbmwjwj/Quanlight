from datetime import date

from quanlight.emit import render_filter_remote, render_list
from quanlight.model import Bundle, Rule


def r(type_, value):
    return Rule(type=type_, value=value, role="core", source="manual")


RULES = [r("ip-cidr", "91.108.4.0/22"), r("host-suffix", "telegram.org"), r("host", "t.me"), r("host", "t.me")]
PROVENANCE = {"telegram-cidr": "sha256:abc"}


def test_render_list_deterministic():
    first = render_list("telegram", RULES, PROVENANCE)
    assert first == render_list("telegram", RULES, PROVENANCE)
    assert date.today().isoformat() not in first
    assert first.endswith("\n")
    assert "# source telegram-cidr: sha256:abc" in first


def test_render_list_order_and_dedupe():
    body = [l for l in render_list("telegram", RULES, PROVENANCE).splitlines() if not l.startswith("#")]
    assert body == [
        "host, t.me, telegram",
        "host-suffix, telegram.org, telegram",
        "ip-cidr, 91.108.4.0/22, telegram",
    ]


def test_render_filter_remote():
    bundles = [
        Bundle("telegram", "d", 40, ()),
        Bundle("apns", "d", 10, ()),
    ]
    lines = render_filter_remote(bundles, "https://cdn.example/q@release").splitlines()
    assert lines[0].startswith("https://cdn.example/q@release/ios/direct-exceptions.list,")
    assert "force-policy=direct" in lines[0]
    assert "/ios/apns.list," in lines[1] and "/ios/telegram.list," in lines[2]
    assert all("force-policy=<proxy-policy>" in l for l in lines[1:3])
    assert lines[-1].startswith("FILTER_LAN,")
