from pathlib import Path

import pytest

from quanlight.sources import SourceError, parse_cidr_list, parse_dnsmasq, parse_telegram_cidr

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
