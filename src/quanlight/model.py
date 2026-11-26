"""构建各阶段共用的核心数据类型。"""

from dataclasses import dataclass

HOST_TYPES = ("host", "host-suffix", "host-wildcard", "host-keyword")
IP_TYPES = ("ip-cidr", "ip6-cidr")
RULE_TYPES = HOST_TYPES + IP_TYPES


@dataclass(frozen=True)
class Rule:
    type: str
    value: str
    source: str
    reason: str | None = None


@dataclass(frozen=True)
class Note:
    """清单中的 [[exclude]] 或 [[keep]]：按值指向一条直连规则，并写明理由。"""

    value: str
    reason: str


@dataclass(frozen=True)
class Bundle:
    name: str
    description: str
    order: int
    rules: tuple[Rule, ...]
    upstream: tuple[str, ...] = ()
    exclude: tuple[Note, ...] = ()
    keep: tuple[Note, ...] = ()


def normalize_host(value: str) -> str:
    """主机名转小写，并去掉末尾的根点。"""
    return value.strip().lower().rstrip(".")
