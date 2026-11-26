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
    nets = parse_telegram_cidr((FIX / "telegram-cidr.txt").read_text())
    assert [str(n) for n in nets] == ["91.108.56.0/22", "149.154.160.0/20", "2001:b28:f23d::/48"]


@pytest.mark.parametrize("text", ["", "\n\n", "<html><body>502 Bad Gateway</body></html>"])
def test_telegram_cidr_rejects_html_and_empty(text):
    with pytest.raises(SourceError):
        parse_telegram_cidr(text)


def test_github_meta_takes_client_facing_keys_only():
    got = [str(n) for n in parse_github_meta((FIX / "github-meta.json").read_text())]
    # 只收录 web、api、git、packages、copilot，去重后按出现顺序
    assert got == [
        "192.30.252.0/22",
        "140.82.112.0/20",
        "2a0a:a440::/29",
        "20.201.28.148/32",
        "20.205.243.166/32",
        "140.82.121.33/32",
        "4.187.247.160/28",
    ]


@pytest.mark.parametrize(
    "text",
    ["", "<html>502</html>", "[]", '{"web": []}', '{"web": ["192.30.252.0/22"]}', '{"web": "x", "api": [], "git": [], "packages": [], "copilot": []}',
     '{"web": ["nope"], "api": [], "git": [], "packages": [], "copilot": []}'],
)
def test_github_meta_rejects_bad_input(text):
    with pytest.raises(SourceError):
        parse_github_meta(text)


def test_google_ipranges_parses_both_versions():
    nets = parse_google_ipranges((FIX / "goog.json").read_text())
    assert [str(n) for n in nets] == ["8.8.4.0/24", "8.34.208.0/20", "2001:4860::/32"]


@pytest.mark.parametrize(
    "text",
    ["", "<html>502</html>", "{}", '{"prefixes": []}', '{"prefixes": [{"service": "x"}]}', '{"prefixes": [{"ipv4Prefix": "bad"}]}'],
)
def test_google_ipranges_rejects_bad_input(text):
    with pytest.raises(SourceError):
        parse_google_ipranges(text)


def test_dnsmasq_parse():
    assert parse_dnsmasq((FIX / "dnsmasq.conf").read_text()) == ["example.cn", "qq.com"]


def test_dnsmasq_rejects_unparsable_line():
    with pytest.raises(SourceError, match="bogus"):
        parse_dnsmasq("server=/qq.com/114.114.114.114\nbogus line\n")


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
