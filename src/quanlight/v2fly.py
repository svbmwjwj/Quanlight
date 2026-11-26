"""展开 v2fly/domain-list-community 数据，导入直连规则并提取反向检查用的境外域名。

数据格式见 https://github.com/v2fly/domain-list-community#structure-of-data
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .model import Rule, normalize_host


class V2flyError(Exception):
    pass


@dataclass(frozen=True)
class Entry:
    kind: str  # domain、full、keyword 或 regexp
    value: str
    attrs: frozenset[str]
    file: str


@dataclass
class ImportResult:
    rules: list[Rule] = field(default_factory=list)
    skipped: list[tuple[Entry, str]] = field(default_factory=list)


def _parse_line(line: str) -> tuple[str, list[str]] | None:
    line = line.split("#", 1)[0].strip()
    if not line:
        return None
    head, *rest = line.split()
    return head, [t for t in rest if t.startswith("@")]  # 丢弃 "&affiliation" 标记


def expand(data_dir: Path, name: str, exclude: Iterable[str] = ()) -> list[Entry]:
    excluded = set(exclude)

    def walk(current: str, stack: tuple[str, ...]) -> list[Entry]:
        if current in stack:
            raise V2flyError(f"include cycle: {' -> '.join(stack + (current,))}")
        path = data_dir / current
        if not path.is_file():
            raise V2flyError(f"missing v2fly file: {current}")
        out: list[Entry] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_line(raw)
            if parsed is None:
                continue
            head, attr_tokens = parsed
            if head.startswith("include:"):
                target = head.removeprefix("include:")
                if target in excluded:
                    continue
                want = frozenset(t[1:] for t in attr_tokens if not t.startswith("@-"))
                deny = frozenset(t[2:] for t in attr_tokens if t.startswith("@-"))
                # 属性过滤作用于完整展开后的结果，包括嵌套引用的文件。
                out += [e for e in walk(target, stack + (current,)) if want <= e.attrs and not e.attrs & deny]
                continue
            kind, _, value = head.partition(":") if ":" in head else ("domain", "", head)
            if kind not in ("keyword", "regexp"):
                value = normalize_host(value)
            out.append(Entry(kind=kind, value=value, attrs=frozenset(t[1:] for t in attr_tokens), file=current))
        return out

    return walk(name, ())


# geolocation-cn 的导入映射（设计文档“直连数据”）：
# 无前缀或 domain: -> host-suffix，full: -> host；@!cn、@ads 与 keyword: 不导入，regexp: 计数丢弃。
def import_direct(entries: Iterable[Entry], source: str) -> ImportResult:
    result = ImportResult()
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        if "!cn" in entry.attrs:
            result.skipped.append((entry, "not-cn"))
        elif "ads" in entry.attrs:
            result.skipped.append((entry, "ads"))
        elif entry.kind == "keyword":
            result.skipped.append((entry, "keyword"))
        elif entry.kind == "regexp":
            result.skipped.append((entry, "regexp"))
        elif entry.kind not in ("domain", "full"):
            raise V2flyError(f"unknown entry kind {entry.kind!r} in {entry.file}")
        else:
            type_ = "host" if entry.kind == "full" else "host-suffix"
            if (type_, entry.value) not in seen:
                seen.add((type_, entry.value))
                result.rules.append(Rule(type=type_, value=entry.value, source=source))
    return result


def foreign_domains(entries: Iterable[Entry]) -> list[str]:
    """反向检查用的境外域名：geolocation-!cn 中去掉带 @cn 的条目，只取 domain 与 full。"""
    return list(dict.fromkeys(e.value for e in entries if e.kind in ("domain", "full") and "cn" not in e.attrs))
