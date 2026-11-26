"""直连数据源（进入列表）与反向检查数据（不进入列表）的地址与解析。"""

import ipaddress
import json
import re

from .match import IPNetwork
from .model import normalize_host

TELEGRAM_CIDR_URL = "https://core.telegram.org/resources/cidr.txt"
GITHUB_META_URL = "https://api.github.com/meta"
GOOGLE_IPRANGES_URL = "https://www.gstatic.com/ipranges/goog.json"
V2FLY_REPO = {
    "repo": "v2fly/domain-list-community",
    "branch": "master",
    "url": "https://codeload.github.com/v2fly/domain-list-community/tar.gz/refs/heads/master",
}
DNSMASQ_APPLE_REPO = {
    "repo": "felixonmars/dnsmasq-china-list",
    "branch": "master",
    "url": "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/apple.china.conf",
}
CHINA_IP_REPO = {
    "repo": "gaoyifan/china-operator-ip",
    "branch": "ip-lists",
    "v4": "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china.txt",
    "v6": "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china6.txt",
}

# 清单中 [[upstream]] 可用的 kind（D-029）。
UPSTREAM_KINDS = ("v2fly", "dnsmasq-apple-china", "china-operator-ip")

# 反向检查用的 GitHub meta 键：客户端会直接访问的网段（D-022）。
GITHUB_META_KEYS = ("web", "api", "git", "packages", "copilot")

_DNSMASQ_RE = re.compile(r"^server=/([^/]+)/[^/]*$")


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


def parse_cidr_list(text: str, what: str = "cidr list") -> list[IPNetwork]:
    return _networks(text, what)


def parse_telegram_cidr(text: str) -> list[IPNetwork]:
    return _networks(text, "telegram-cidr")


def _json_object(text: str, what: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise SourceError(f"{what}: not valid JSON") from exc
    if not isinstance(data, dict):
        raise SourceError(f"{what}: expected a JSON object")
    return data


def _parse_net(value: object, what: str) -> IPNetwork:
    try:
        return ipaddress.ip_network(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise SourceError(f"{what}: unparsable prefix {str(value)[:60]!r}") from exc


def _unique(nets: list[IPNetwork]) -> list[IPNetwork]:
    return list(dict.fromkeys(nets))


def parse_github_meta(text: str) -> list[IPNetwork]:
    data = _json_object(text, "github-meta")
    nets: list[IPNetwork] = []
    for key in GITHUB_META_KEYS:
        values = data.get(key)
        # 任一键缺失或不是列表，视为格式变化，构建失败以便人工复核
        if not isinstance(values, list):
            raise SourceError(f"github-meta: missing list {key!r}")
        nets += [_parse_net(v, "github-meta") for v in values]
    if not nets:
        raise SourceError("github-meta: no networks found")
    return _unique(nets)


def parse_google_ipranges(text: str) -> list[IPNetwork]:
    data = _json_object(text, "google-ipranges")
    prefixes = data.get("prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        raise SourceError("google-ipranges: no prefixes found")
    nets: list[IPNetwork] = []
    for entry in prefixes:
        value = (entry.get("ipv4Prefix") or entry.get("ipv6Prefix")) if isinstance(entry, dict) else None
        if value is None:
            raise SourceError(f"google-ipranges: entry without prefix {str(entry)[:60]!r}")
        nets.append(_parse_net(value, "google-ipranges"))
    return _unique(nets)


def parse_dnsmasq(text: str) -> list[str]:
    """解析 server=/<域名>/<DNS> 行；出现其他格式的行即视为上游格式变化。"""
    domains: dict[str, None] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if (m := _DNSMASQ_RE.match(line)) is None:
            raise SourceError(f"dnsmasq-china-list: unparsable line {line[:60]!r}")
        domains.setdefault(normalize_host(m.group(1)))
    if not domains:
        raise SourceError("dnsmasq-china-list: no domains found")
    return list(domains)
