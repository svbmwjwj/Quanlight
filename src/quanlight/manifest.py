"""Read, validate and write service bundle manifests (TOML)."""

import ipaddress
import json
import re
import tomllib
from datetime import date
from pathlib import Path

from .model import HOST_TYPES, ROLES, RULE_TYPES, Bundle, Rule, normalize_host

_HOST_RE = re.compile(r"^[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?(\.[a-z0-9_]([a-z0-9_-]*[a-z0-9_])?)*$")
_WILDCARD_RE = re.compile(r"^[a-z0-9_.*?-]+$")


def _normalize_value(type_: str, value: str) -> str:
    return normalize_host(value) if type_ in HOST_TYPES else value.strip()


def _rule_from_table(table: dict) -> Rule:
    type_ = table["type"]
    return Rule(
        type=type_,
        value=_normalize_value(type_, table["value"]),
        role=table["role"],
        source=table["source"],
        reason=table.get("reason"),
        breadth=table.get("breadth"),
        review_by=table.get("review_by"),
        exempt=tuple(normalize_host(e) for e in table.get("exempt", ())),
        asn_verified=table.get("asn_verified"),
    )


def load_bundle(path: Path) -> Bundle:
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return Bundle(
        name=data["name"],
        description=data["description"],
        order=data["order"],
        rules=tuple(_rule_from_table(t) for t in data.get("rule", ())),
        upstream=tuple(t["kind"] for t in data.get("upstream", ())),
        uses=tuple(data.get("uses", ())),
        v2fly_exclude=tuple(data.get("v2fly_exclude", ())),
    )


def load_bundles(directory: Path) -> list[Bundle]:
    bundles = [load_bundle(p) for p in sorted(directory.glob("*.toml"))]
    return sorted(bundles, key=lambda b: (b.order, b.name))


def _value_error(rule: Rule) -> str | None:
    t, v = rule.type, rule.value
    if not v or "," in v or any(c.isspace() for c in v):
        return "value must be non-empty without commas or whitespace"
    if t in ("host", "host-suffix") and not _HOST_RE.match(v):
        return "not a valid host name"
    if t == "host-wildcard" and (not _WILDCARD_RE.match(v) or not any(c in v for c in "*?")):
        return "not a valid wildcard pattern"
    if t in ("ip-cidr", "ip6-cidr"):
        try:
            net = ipaddress.ip_network(v)
        except ValueError:
            return "not a valid network"
        if (t == "ip-cidr") != (net.version == 4):
            return f"{t} requires an IPv{4 if t == 'ip-cidr' else 6} network"
    if t == "ip-asn" and not v.isdigit():
        return "ASN must be digits only"
    return None


def validate_bundle(bundle: Bundle, today: date) -> list[str]:
    errors: list[str] = []
    for rule in bundle.rules:
        where = f"{bundle.name}: {rule.type}, {rule.value}"
        if rule.type not in RULE_TYPES:
            errors.append(f"{where}: unsupported rule type {rule.type}")
            continue
        if rule.role not in ROLES:
            errors.append(f"{where}: unknown role {rule.role}")
        if problem := _value_error(rule):
            errors.append(f"{where}: {problem}")
        needs_reason = (
            rule.type in ("host-keyword", "ip-asn") or rule.breadth == "broad" or bool(rule.exempt)
        )
        if needs_reason and not rule.reason:
            errors.append(f"{where}: reason is required")
        if rule.breadth not in (None, "broad"):
            errors.append(f"{where}: breadth must be 'broad' when set")
        if rule.breadth == "broad":
            if rule.review_by is None:
                errors.append(f"{where}: review_by is required for broad rules")
            elif rule.review_by < today:
                errors.append(f"{where}: review_by {rule.review_by} has passed")
        if rule.type == "ip-asn" and not rule.asn_verified:
            errors.append(f"{where}: asn_verified is required")
    return errors


def _s(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _arr(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(_s(v) for v in values) + "]"


def dump_bundle(bundle: Bundle) -> str:
    lines = [
        f"name = {_s(bundle.name)}",
        f"description = {_s(bundle.description)}",
        f"order = {bundle.order}",
    ]
    if bundle.uses:
        lines.append(f"uses = {_arr(bundle.uses)}")
    if bundle.v2fly_exclude:
        lines.append(f"v2fly_exclude = {_arr(bundle.v2fly_exclude)}")
    for rule in bundle.rules:
        lines += ["", "[[rule]]", f"type = {_s(rule.type)}", f"value = {_s(rule.value)}",
                  f"role = {_s(rule.role)}", f"source = {_s(rule.source)}"]
        if rule.reason is not None:
            lines.append(f"reason = {_s(rule.reason)}")
        if rule.breadth is not None:
            lines.append(f"breadth = {_s(rule.breadth)}")
        if rule.review_by is not None:
            lines.append(f"review_by = {rule.review_by.isoformat()}")
        if rule.exempt:
            lines.append(f"exempt = {_arr(rule.exempt)}")
        if rule.asn_verified is not None:
            lines.append(f"asn_verified = {_s(rule.asn_verified)}")
    for kind in bundle.upstream:
        lines += ["", "[[upstream]]", f"kind = {_s(kind)}"]
    return "\n".join(lines) + "\n"
