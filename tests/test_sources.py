from pathlib import Path

import pytest

from quanlight.sources import (
    SourceError,
    parse_cidr_list,
    parse_dnsmasq,
    parse_github_meta,
    parse_google_ipranges,
    parse_telegram_cidr,
)

FIX = Path(__file__).parent / "fixtures"


def test_telegram_cidr_parses_both_versions():
    rules = parse_telegram_cidr((FIX / "telegram-cidr.txt").read_text(), bundle="telegram")
    got = {(r.type, r.value) for r in rules}
    assert got == {
        ("ip-cidr", "91.108.56.0/22"),
        ("ip-cidr", "149.154.160.0/20"),
        ("ip6-cidr", "2001:b28:f23d::/48"),
    }
    assert all(r.source == "official:https://core.telegram.org/resources/cidr.txt" for r in rules)


@pytest.mark.parametrize("text", ["", "\n\n", "<html><body>502 Bad Gateway</body></html>"])
def test_telegram_cidr_rejects_html_and_empty(text):
    with pytest.raises(SourceError):
        parse_telegram_cidr(text, bundle="telegram")


def test_github_meta_takes_client_facing_keys_only():
    rules = parse_github_meta((FIX / "github-meta.json").read_text(), bundle="github")
    got = [(r.type, r.value) for r in rules]
    # 只收录 web、api、git、packages、copilot，去重后按出现顺序
    assert got == [
        ("ip-cidr", "192.30.252.0/22"),
        ("ip-cidr", "140.82.112.0/20"),
        ("ip6-cidr", "2a0a:a440::/29"),
        ("ip-cidr", "20.201.28.148/32"),
        ("ip-cidr", "20.205.243.166/32"),
        ("ip-cidr", "140.82.121.33/32"),
        ("ip-cidr", "4.187.247.160/28"),
    ]
    assert all(r.role == "core" and r.source == "official:https://api.github.com/meta" for r in rules)


@pytest.mark.parametrize(
    "text",
    ["", "<html>502</html>", "[]", '{"web": []}', '{"web": ["192.30.252.0/22"]}', '{"web": "x", "api": [], "git": [], "packages": [], "copilot": []}',
     '{"web": ["nope"], "api": [], "git": [], "packages": [], "copilot": []}'],
)
def test_github_meta_rejects_bad_input(text):
    with pytest.raises(SourceError):
        parse_github_meta(text, bundle="github")


def test_google_ipranges_parses_both_versions():
    rules = parse_google_ipranges((FIX / "goog.json").read_text(), bundle="google")
    assert [(r.type, r.value) for r in rules] == [
        ("ip-cidr", "8.8.4.0/24"),
        ("ip-cidr", "8.34.208.0/20"),
        ("ip6-cidr", "2001:4860::/32"),
    ]
    assert all(r.role == "core" and r.source == "official:https://www.gstatic.com/ipranges/goog.json" for r in rules)


@pytest.mark.parametrize(
    "text",
    ["", "<html>502</html>", "{}", '{"prefixes": []}', '{"prefixes": [{"service": "x"}]}', '{"prefixes": [{"ipv4Prefix": "bad"}]}'],
)
def test_google_ipranges_rejects_bad_input(text):
    with pytest.raises(SourceError):
        parse_google_ipranges(text, bundle="google")


def test_dnsmasq_parse():
    assert parse_dnsmasq((FIX / "dnsmasq.conf").read_text()) == {"example.cn", "qq.com"}


def test_dnsmasq_rejects_empty():
    with pytest.raises(SourceError):
        parse_dnsmasq("# nothing\n")


def test_cidr_list_parses_and_rejects_empty():
    nets = parse_cidr_list("1.0.1.0/24\n2001:250::/30\n")
    assert [str(n) for n in nets] == ["1.0.1.0/24", "2001:250::/30"]
    with pytest.raises(SourceError):
        parse_cidr_list("\n")
    with pytest.raises(SourceError):
        parse_cidr_list("<html>")
