"""上游数据（进入列表）与检查数据（不进入列表）的解析。"""

import ipaddress
import json

from .match import IPNetwork
from .model import Rule, normalize_host

TELEGRAM_CIDR_URL = "https://core.telegram.org/resources/cidr.txt"
GITHUB_META_URL = "https://api.github.com/meta"
GOOGLE_IPRANGES_URL = "https://www.gstatic.com/ipranges/goog.json"

# GitHub meta 中客户端会直接访问的网段（D-022）。
# 不收录：hooks、actions、actions_macos、importer、github_enterprise_importer 是 GitHub 主动发起连接
# 或运行器所在的网段；codespaces 是用户虚拟机；shared_ingress 未见文档说明；pages 已被 web 覆盖。
GITHUB_META_KEYS = ("web", "api", "git", "packages", "copilot")

# 每次构建同步的官方数据，键为清单中 [[upstream]] 的 kind。
UPSTREAM_KINDS: dict[str, str] = {
    "telegram-cidr": TELEGRAM_CIDR_URL,
    "github-meta": GITHUB_META_URL,
    "google-ipranges": GOOGLE_IPRANGES_URL,
}

# 检查数据：只用于发现国内流量被误送代理。
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


def _ip_rules(nets: list[IPNetwork], url: str) -> list[Rule]:
    """网段转为规则，去重并保持原有顺序。"""
    rules: dict[str, Rule] = {}
    for n in nets:
        rules.setdefault(
            str(n), Rule(type="ip-cidr" if n.version == 4 else "ip6-cidr", value=str(n), role="core", source=f"official:{url}")
        )
    return list(rules.values())


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


def parse_github_meta(text: str, bundle: str) -> list[Rule]:
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
    return _ip_rules(nets, GITHUB_META_URL)


def parse_google_ipranges(text: str, bundle: str) -> list[Rule]:
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
    return _ip_rules(nets, GOOGLE_IPRANGES_URL)


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
