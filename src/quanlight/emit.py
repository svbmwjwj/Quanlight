"""Render Quantumult X filter lists and the [filter_remote] subscription snippet."""

from collections.abc import Mapping, Sequence

from .model import RULE_TYPES, Bundle, Rule

PROXY_POLICY_PLACEHOLDER = "<proxy-policy>"
_REMOTE_OPTS = "update-interval=86400, opt-parser=false, enabled=true"


def render_list(name: str, rules: Sequence[Rule], provenance: Mapping[str, str]) -> str:
    unique = sorted({(r.type, r.value) for r in rules}, key=lambda k: (RULE_TYPES.index(k[0]), k[1]))
    header = [f"# quanlight {name}", f"# rules: {len(unique)}"]
    header += [f"# source {key}: {provenance[key]}" for key in sorted(provenance)]
    body = [f"{type_}, {value}, {name}" for type_, value in unique]
    return "\n".join(header + body) + "\n"


def render_filter_remote(bundles: Sequence[Bundle], base_url: str) -> str:
    base = base_url.rstrip("/")
    lines = [f"{base}/ios/direct-exceptions.list, tag=quanlight-direct-exceptions, force-policy=direct, {_REMOTE_OPTS}"]
    for bundle in sorted(bundles, key=lambda b: (b.order, b.name)):
        lines.append(
            f"{base}/ios/{bundle.name}.list, tag=quanlight-{bundle.name}, "
            f"force-policy={PROXY_POLICY_PLACEHOLDER}, {_REMOTE_OPTS}"
        )
    lines.append("FILTER_LAN, tag=LAN, force-policy=direct, enabled=true")
    return "\n".join(lines) + "\n"
