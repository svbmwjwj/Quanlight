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
class UpstreamSpec:
    """清单中的一个 [[upstream]]；kind 为 v2fly 时 file 指 v2fly 数据文件，apps 写它服务的常用应用。"""

    kind: str
    file: str | None = None
    apps: str | None = None
    skip_includes: tuple[str, ...] = ()  # 展开时跳过的 include 子文件
    allow_foreign: bool = False  # 本人有意直连：这个数据源的规则不参与反向检查
    reason: str | None = None  # allow_foreign 的理由

    @property
    def key(self) -> str:
        """构建内部与产物文件头使用的数据源名。"""
        return f"{self.kind}:{self.file}" if self.file else self.kind


@dataclass(frozen=True)
class Bundle:
    name: str
    description: str
    order: int
    rules: tuple[Rule, ...]
    upstream: tuple[UpstreamSpec, ...] = ()
    exclude: tuple[Note, ...] = ()
    keep: tuple[Note, ...] = ()


def normalize_host(value: str) -> str:
    """主机名转小写，并去掉末尾的根点。"""
    return value.strip().lower().rstrip(".")
