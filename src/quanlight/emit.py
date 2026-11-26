"""渲染 Quantumult X 分流列表与 [filter_remote] 订阅片段。"""

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


# 真机探针：验证设计中尚未确定的匹配语义。
# 每个用例包含：按订阅顺序排列的远程列表 (类型, 值, 策略)、
# 可选的 [filter_local] 规则，以及要在 Safari 中打开的主机。
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


def mirror_bases(owner: str, repo: str) -> dict[str, str]:
    """发布分支的基础地址：GitHub 本身与境内可用的镜像。"""
    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/release"
    return {
        "github": raw,
        "ghfast": f"https://ghfast.top/{raw}",
        "jsdelivr-fastly": f"https://fastly.jsdelivr.net/gh/{owner}/{repo}@release",
        "jsdelivr": f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@release",
    }


def render_release_readme(bundles: Sequence[Bundle], owner: str, repo: str) -> str:
    bases = mirror_bases(owner, repo)
    lines = [
        "# Quanlight lists",
        "",
        f"Built from https://github.com/{owner}/{repo}. Replace `<proxy-policy>` with your own policy names.",
        "",
        "## Base URLs",
        "",
        f"- GitHub: `{bases['github']}`",
        f"- Mainland China (GitHub proxy, third party): `{bases['ghfast']}`",
        f"- jsDelivr (Fastly): `{bases['jsdelivr-fastly']}`",
        f"- jsDelivr: `{bases['jsdelivr']}`",
        "",
        "## Subscribe from GitHub",
        "",
        "```",
        "[filter_remote]",
        render_filter_remote(bundles, bases["github"]).rstrip("\n"),
        "```",
        "",
        "## Subscribe from mainland China",
        "",
        "```",
        "[filter_remote]",
        render_filter_remote(bundles, bases["ghfast"]).rstrip("\n"),
        "```",
    ]
    return "\n".join(lines) + "\n"
