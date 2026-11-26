"""Parsers for upstream data (bundled into lists) and check data (never bundled)."""

import ipaddress

from .match import IPNetwork
from .model import Rule, normalize_host

TELEGRAM_CIDR_URL = "https://core.telegram.org/resources/cidr.txt"

# Official data synced on every build, keyed by the manifest's [[upstream]] kind.
UPSTREAM_KINDS: dict[str, str] = {"telegram-cidr": TELEGRAM_CIDR_URL}

# Check data: used only to detect mis-routing of mainland China traffic.
CHECK_SOURCES: dict[str, dict[str, str]] = {
    "dnsmasq-china-list": {
        "repo": "felixonmars/dnsmasq-china-list",
        "branch": "master",
        "url": "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/accelerated-domains.china.conf",
    },
    "china-operator-ip-v4": {
        "repo": "gaoyifan/china-operator-ip",
        "branch": "ip-lists",
        "url": "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china.txt",
    },
    "china-operator-ip-v6": {
        "repo": "gaoyifan/china-operator-ip",
        "branch": "ip-lists",
        "url": "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china6.txt",
    },
    "v2fly": {
        "repo": "v2fly/domain-list-community",
        "branch": "master",
        "url": "https://codeload.github.com/v2fly/domain-list-community/tar.gz/refs/heads/master",
    },
}


class SourceError(Exception):
    pass


def _networks(text: str, what: str) -> list[IPNetwork]:
    nets: list[IPNetwork] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            nets.append(ipaddress.ip_network(line))
        except ValueError as exc:
            raise SourceError(f"{what}: unparsable line {line[:60]!r}") from exc
    if not nets:
        raise SourceError(f"{what}: no networks found")
    return nets


def parse_telegram_cidr(text: str, bundle: str) -> list[Rule]:
    source = f"official:{TELEGRAM_CIDR_URL}"
    return [
        Rule(type="ip-cidr" if n.version == 4 else "ip6-cidr", value=str(n), role="core", source=source)
        for n in _networks(text, "telegram-cidr")
    ]


def parse_dnsmasq(text: str) -> set[str]:
    domains = {
        normalize_host(line.split("/")[1])
        for line in text.splitlines()
        if line.startswith("server=/") and line.count("/") >= 2
    }
    if not domains:
        raise SourceError("dnsmasq-china-list: no domains found")
    return domains


def parse_cidr_list(text: str) -> list[IPNetwork]:
    return _networks(text, "cidr list")
