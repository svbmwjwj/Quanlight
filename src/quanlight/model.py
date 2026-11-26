"""构建各阶段共用的核心数据类型。"""

from dataclasses import dataclass
from datetime import date

HOST_TYPES = ("host", "host-suffix", "host-wildcard", "host-keyword")
IP_TYPES = ("ip-cidr", "ip6-cidr", "ip-asn")
RULE_TYPES = HOST_TYPES + IP_TYPES
ROLES = ("core", "dependency", "cn-exception")


@dataclass(frozen=True)
class Rule:
    type: str
    value: str
    role: str
    source: str
    reason: str | None = None
    breadth: str | None = None
    review_by: date | None = None
    exempt: tuple[str, ...] = ()
    asn_verified: str | None = None


@dataclass(frozen=True)
class Bundle:
    name: str
    description: str
    order: int
    rules: tuple[Rule, ...]
    upstream: tuple[str, ...] = ()
    uses: tuple[str, ...] = ()
    v2fly_exclude: tuple[str, ...] = ()
    v2fly_ignore: tuple[str, ...] = ()  # 有意不收录的上游条目


def normalize_host(value: str) -> str:
    """主机名转小写，并去掉末尾的根点。"""
    return value.strip().lower().rstrip(".")
