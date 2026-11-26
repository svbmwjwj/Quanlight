"""渲染 Quantumult X 分流列表、[filter_remote] 订阅片段与探针列表。"""

import json
from collections.abc import Collection, Sequence

from .model import RULE_TYPES, Rule

# 本人配置里代理托底策略的名称；他人使用时改成自己的策略名
PROXY_POLICY = "hello world ：）"
# 规则集只在本人手动更新时拉取，-1 关闭自动同步（D-023）
_REMOTE_OPTS = "update-interval=-1, opt-parser=false, enabled=true"


def render_list(name: str, rules: Sequence[Rule], header: Sequence[str]) -> str:
    """三列格式；文件头写数据来源与上游版本，不写生成时间，内容不变时输出也不变。"""
    unique = sorted({(r.type, r.value) for r in rules}, key=lambda k: (RULE_TYPES.index(k[0]), k[1]))
    lines = [f"# quanlight {name}", f"# rules: {len(unique)}", *header]
    lines += [f"{type_}, {value}, {name}" for type_, value in unique]
    return "\n".join(lines) + "\n"


def render_filter_remote(names: Sequence[str], direct: Collection[str], base_url: str) -> str:
    """names 按订阅顺序排列；直连包 force-policy=direct，其余强制走代理。"""
    base = base_url.rstrip("/")
    lines = []
    for name in names:
        policy = "direct" if name in direct else PROXY_POLICY
        lines.append(f"{base}/{name}.list, tag={name}, force-policy={policy}, {_REMOTE_OPTS}")
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
        [("host-suffix", "example.org", "reject"), ("host", "www.example.org", "direct")],
        None,
        ["www.example.org"],
    ),
    "local": (
        [("host", "www.example.net", "reject")],
        "host, www.example.net, direct",
        ["www.example.net"],
    ),
    "wildcard": (
        [("host-wildcard", "*.iana.org", "reject")],
        None,
        ["www.iana.org", "iana.org"],
    ),
    "cname": (
        [("host", "www.microsoft.com-c-3.edgekey.net", "reject")],
        None,
        ["www.microsoft.com"],
    ),
}

PROBE_PORT = 9999
PROBE_PATH = "quanlight-probe"


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


def render_probe_profile(script_ref: str = "quanlight-probe.js", remote_base: str | None = None) -> dict[str, str]:
    """生成可单独切换使用的探针配置。

    remote_base 为空时，探针列表由本机 http_backend 脚本提供；Quantumult X 拉取规则资源不经过自身隧道，
    访问不到 127.0.0.1:9999，所以真机探针应传入 remote_base，从远程地址下载列表文件。
    """
    lists: dict[str, str] = {}
    remote: list[str] = []
    local: list[str] = []
    for case, (rules, local_rule, visit) in PROBE_CASES.items():
        remote.append(f"# {case}: open " + ", ".join(visit))
        for i, (type_, value, policy) in enumerate(rules, start=1):
            name = f"{case}-{i}"
            lists[f"{name}.list"] = f"{type_}, {value}, {name}\n"
            base = remote_base.rstrip("/") if remote_base else f"http://127.0.0.1:{PROBE_PORT}/{PROBE_PATH}"
            remote.append(f"{base}/{name}.list, tag={name}, force-policy={policy}, enabled=true")
        if local_rule:
            local.append(local_rule)
    profile = "\n".join(
        [
            "# Quanlight 匹配语义探针配置：只含探针规则，不含节点与私人信息。",
            "# 测完请切回原来的配置。",
            "",
            "[general]",
            "server_check_url = http://cp.cloudflare.com/generate_204",
            "",
            "[dns]",
            "no-system",
            "doh-server = https://223.5.5.5/dns-query",
            "",
            "[policy]",
            "",
            "[server_remote]",
            "",
            "[filter_remote]",
            *remote,
            "",
            "[rewrite_remote]",
            "",
            "[server_local]",
            "",
            "[filter_local]",
            *local,
            "final, direct",
            "",
            "[rewrite_local]",
            "",
            "[task_local]",
            "",
            "[http_backend]",
            *([] if remote_base else [f"{script_ref}, tag=quanlight-probe, path=^/{PROBE_PATH}/, enabled=true"]),
            "",
            "[mitm]",
        ]
    ) + "\n"
    entries = ",\n".join(f"  {json.dumps(k)}: {json.dumps(v)}" for k, v in lists.items())
    script = (
        "// Quanlight 探针后端：按路径返回探针列表。\n"
        f"const lists = {{\n{entries}\n}};\n"
        "const name = $request.path.split(\"/\").pop();\n"
        "const body = lists[name];\n"
        "$done(body === undefined\n"
        "  ? { status: \"HTTP/1.1 404 Not Found\", headers: { Connection: \"Close\" }, body: \"not found\\n\" }\n"
        "  : { status: \"HTTP/1.1 200 OK\", headers: { \"Content-Type\": \"text/plain\", Connection: \"Close\" }, body: body });\n"
    )
    if remote_base:
        return {"quanlight-probe.conf": profile, **lists}
    return {"quanlight-probe.conf": profile, "quanlight-probe.js": script}


def mirror_bases(owner: str, repo: str) -> dict[str, str]:
    """发布分支的基础地址：GitHub 本身与境内可用的镜像。"""
    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/release"
    return {
        "github": raw,
        "ghfast": f"https://ghfast.top/{raw}",
        "jsdelivr-fastly": f"https://fastly.jsdelivr.net/gh/{owner}/{repo}@release",
        "jsdelivr": f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@release",
    }


def render_release_readme(names: Sequence[str], direct: Collection[str], owner: str, repo: str) -> str:
    bases = mirror_bases(owner, repo)

    def snippet(base: str) -> list[str]:
        return [
            "```",
            "[filter_remote]",
            render_filter_remote(names, direct, base).rstrip("\n"),
            "",
            "[filter_local]",
            "# personal exceptions go here",
            f"final, {PROXY_POLICY}",
            "```",
        ]

    lines = [
        "# Quanlight lists",
        "",
        f"Built from https://github.com/{owner}/{repo}. Mainland China domains and networks connect directly;",
        "everything else falls through to `final` and goes through your proxy.",
        "",
        f"`{PROXY_POLICY}` is the proxy policy in the author's profile; replace it with yours. Every line needs its `force-policy`;",
        "without it the rules point at a policy that does not exist.",
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
        *snippet(bases["github"]),
        "",
        "## Subscribe from mainland China",
        "",
        *snippet(bases["ghfast"]),
    ]
    return "\n".join(lines) + "\n"
