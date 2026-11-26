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


# On-device probes for the rule-matching questions the design leaves open.
# Each case: remote lists as (type, value, policy) in subscription order,
# an optional [filter_local] line, and the hosts to open in Safari.
PROBE_CASES: dict[str, tuple[list[tuple[str, str, str]], str | None, list[str]]] = {
    "order": (
        [("host-suffix", "example.com", "reject"), ("host-suffix", "example.com", "direct")],
        None,
        ["www.example.com"],
    ),
    "type": (
        [("host-suffix", "example.com", "reject"), ("host", "www.example.com", "direct")],
        None,
        ["www.example.com"],
    ),
    "local": (
        [("host", "www.example.com", "reject")],
        "host, www.example.com, direct",
        ["www.example.com"],
    ),
    "wildcard": (
        [("host-wildcard", "*.example.com", "reject")],
        None,
        ["www.example.com", "example.com"],
    ),
    "cname": (
        [("host", "www.microsoft.com-c-3.edgekey.net", "reject")],
        None,
        ["www.microsoft.com"],
    ),
}


def render_probe(case: str, base_url: str) -> dict[str, str]:
    remote, local, visit = PROBE_CASES[case]
    base = base_url.rstrip("/")
    files: dict[str, str] = {}
    snippet = [f"# probe {case}: open " + ", ".join(visit), "# reject = blocked, direct = loads"]
    if local:
        snippet += ["", "[filter_local]", local]
    snippet += ["", "[filter_remote]"]
    for i, (type_, value, policy) in enumerate(remote, start=1):
        name = f"probe-{case}-{i}.list"
        files[name] = f"{type_}, {value}, probe-{case}-{i}\n"
        snippet.append(f"{base}/{name}, tag=probe-{case}-{i}, force-policy={policy}, enabled=true")
    files[f"probe-{case}.conf"] = "\n".join(snippet) + "\n"
    return files
