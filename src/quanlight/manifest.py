"""读取与校验清单（TOML）。"""

import ipaddress
import re
import tomllib
from pathlib import Path

from .model import HOST_TYPES, RULE_TYPES, Bundle, Note, Rule, normalize_host
from .sources import UPSTREAM_KINDS

_HOST_RE = re.compile(r"^[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?(\.[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?)*$")
_WILDCARD_RE = re.compile(r"^[a-z0-9_.*?-]+$")
_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# 构建自身的策略占用的名字。
RESERVED_NAMES = frozenset({"direct", "reject", "proxy", "final"})
# 手写规则 source 的取值：official:<网址>、observed、manual。
_MANUAL_SOURCES = ("observed", "manual")

_BUNDLE_KEYS = {"name", "description", "order", "rule", "upstream", "exclude", "keep"}
_RULE_KEYS = {"type", "value", "source", "reason"}
_NOTE_KEYS = {"value", "reason"}


class ManifestError(Exception):
    pass


def _normalize_value(type_: str, value: str) -> str:
    return normalize_host(value) if type_ in HOST_TYPES else value.strip()


def _check_keys(table: dict, allowed: set[str], where: str) -> None:
    # 拒绝未知字段，避免旧机制（role、breadth 等）残留在清单里被悄悄忽略
    if unknown := sorted(set(table) - allowed):
        raise ManifestError(f"{where}: unknown keys {unknown}")


def _rule_from_table(table: dict, where: str) -> Rule:
    _check_keys(table, _RULE_KEYS, where)
    type_ = table["type"]
    return Rule(
        type=type_,
        value=_normalize_value(type_, table["value"]),
        source=table["source"],
        reason=table.get("reason"),
    )


def _note_from_table(table: dict, where: str) -> Note:
    _check_keys(table, _NOTE_KEYS, where)
    return Note(value=normalize_host(table.get("value", "")), reason=table.get("reason", ""))


def load_bundle(path: Path) -> Bundle:
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    _check_keys(data, _BUNDLE_KEYS, path.name)
    return Bundle(
        name=data["name"],
        description=data["description"],
        order=data["order"],
        rules=tuple(_rule_from_table(t, f"{path.name} [[rule]]") for t in data.get("rule", ())),
        upstream=tuple(t["kind"] for t in data.get("upstream", ())),
        exclude=tuple(_note_from_table(t, f"{path.name} [[exclude]]") for t in data.get("exclude", ())),
        keep=tuple(_note_from_table(t, f"{path.name} [[keep]]") for t in data.get("keep", ())),
    )


def check_bundle_files(directory: Path) -> list[str]:
    """清单的 name 必须与文件名一致，同时保证包名不重复。"""
    errors = []
    for path in sorted(directory.glob("*.toml")):
        with path.open("rb") as fh:
            name = tomllib.load(fh).get("name")
        if name != path.stem:
            errors.append(f"{path.name}: name {name!r} must equal the file name {path.stem!r}")
    return errors


def load_bundles(directory: Path) -> list[Bundle]:
    bundles = [load_bundle(p) for p in sorted(directory.glob("*.toml"))]
    return sorted(bundles, key=lambda b: (b.order, b.name))


def value_error(type_: str, value: str) -> str | None:
    """规则值不合法时返回原因；上游导入的条目也用它校验。"""
    if not value or "," in value or any(c.isspace() for c in value):
        return "value must be non-empty without commas or whitespace"
    if type_ in ("host", "host-suffix") and not _HOST_RE.match(value):
        return "not a valid host name"
    if type_ == "host-wildcard" and (not _WILDCARD_RE.match(value) or not any(c in value for c in "*?")):
        return "not a valid wildcard pattern"
    if type_ in ("ip-cidr", "ip6-cidr"):
        try:
            net = ipaddress.ip_network(value)
        except ValueError:
            return "not a valid network"
        if (type_ == "ip-cidr") != (net.version == 4):
            return f"{type_} requires an IPv{4 if type_ == 'ip-cidr' else 6} network"
    return None


def validate_bundle(bundle: Bundle) -> list[str]:
    errors: list[str] = []
    if not _NAME_RE.match(bundle.name) or bundle.name in RESERVED_NAMES:
        errors.append(f"{bundle.name!r}: bundle name must be kebab-case and not one of {sorted(RESERVED_NAMES)}")
    for kind in bundle.upstream:
        if kind not in UPSTREAM_KINDS:
            errors.append(f"{bundle.name}: unknown upstream kind {kind!r}")
    for rule in bundle.rules:
        where = f"{bundle.name}: {rule.type}, {rule.value}"
        if rule.type not in RULE_TYPES:
            errors.append(f"{where}: unsupported rule type {rule.type}")
            continue
        if problem := value_error(rule.type, rule.value):
            errors.append(f"{where}: {problem}")
        if rule.source not in _MANUAL_SOURCES and not rule.source.startswith("official:https://"):
            errors.append(f"{where}: source must be official:<https url>, observed or manual")
        if (rule.source in _MANUAL_SOURCES or rule.type == "host-keyword") and not rule.reason:
            errors.append(f"{where}: reason is required")
    for section, notes in (("exclude", bundle.exclude), ("keep", bundle.keep)):
        for note in notes:
            if not note.value or not note.reason:
                errors.append(f"{bundle.name}: [[{section}]] {note.value!r} needs a value and a reason")
    return errors
