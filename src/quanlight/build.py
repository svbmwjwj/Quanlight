"""构建：合并清单与上游数据，运行检查，写出列表与报告。"""

import dataclasses
import ipaddress
import re
import shutil
import tomllib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .check import DIRECT, Hit, domain_hits, network_hits, shadowed
from .emit import render_list, render_release_readme
from .manifest import check_bundle_files, load_bundles, validate_bundle, value_error
from .match import IPNetwork, Router, RuleList
from .model import Bundle, Rule

OUTPUT_MARKER = ".quanlight-dist"  # 标记本工具可以整体替换的输出目录
# 订阅时 force-policy=direct 的包；其余包强制走代理（D-026、D-027）。
DIRECT_BUNDLES = frozenset({"china"})
PROTECTED_BUNDLE = "apns"  # 必须先于直连列表命中的包
FINAL = "final"
# 条目数低于上一版的这个比例时视为上游异常
MIN_RATIO = 0.5
_MAX_LISTED = 50  # 报告中逐条列出的上限
_UPSTREAM_HEADER_RE = re.compile(r"^# upstream (\S+): \S+ \(entries: (\d+)\)$")


@dataclass
class Upstream:
    """一个直连数据源同步并解析后的结果。"""

    kind: str  # UpstreamSpec.key
    version: str
    rules: list[Rule]
    skipped: dict[str, list[str]] = field(default_factory=dict)  # 原因 -> 未导入的条目


@dataclass
class CheckData:
    domains: dict[str, list[str]]  # 数据集 -> 境外域名
    networks: dict[str, list[IPNetwork]]  # 数据集 -> 境外网段
    provenance: dict[str, str]  # 数据集 -> 版本


@dataclass
class SourceStats:
    version: str
    entries: int  # 上游解析出的条目数
    added: int  # 剔除与去重后进入列表的条数


@dataclass
class BuildReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    sizes: dict[str, int] = field(default_factory=dict)
    sources: dict[str, SourceStats] = field(default_factory=dict)
    skipped: dict[str, list[str]] = field(default_factory=dict)
    check_versions: dict[str, str] = field(default_factory=dict)
    redundant: dict[str, int] = field(default_factory=dict)  # 列表 -> 去掉的冗余后缀条数
    hits: list[Hit] = field(default_factory=list)  # 未被 [[keep]] 豁免的命中
    kept: list[Hit] = field(default_factory=list)
    allowed: list[Hit] = field(default_factory=list)  # 来自 allow_foreign 数据源的命中

    def to_markdown(self) -> str:
        lines = ["## quanlight build", "", f"Result: {'FAILED' if self.errors else 'OK'}", ""]
        if self.errors:
            lines += ["### Errors", ""] + [f"- {e}" for e in self.errors] + [""]
        if self.warnings:
            lines += ["### Warnings", ""] + [f"- {w}" for w in self.warnings] + [""]
        if self.counts:
            lines += ["### Lists", "", "| list | rules | bytes |", "|---|---|---|"]
            lines += [f"| {k} | {v} | {self.sizes.get(k, '-')} |" for k, v in self.counts.items()] + [""]
        if self.sources:
            lines += ["### Direct data", "", "| source | version | entries | added |", "|---|---|---|---|"]
            lines += [f"| {k} | {s.version} | {s.entries} | {s.added} |" for k, s in self.sources.items()] + [""]
        for name, n in self.redundant.items():
            lines.append(f"- {name}: dropped {n} host-suffix rules covered by a shorter suffix")
        for reason, values in sorted(self.skipped.items()):
            lines.append(f"- not imported ({reason}): {len(values)}")
            if reason == "keyword":
                lines += [f"  - `{v}`" for v in values]
        if self.skipped or self.redundant:
            lines.append("")
        if self.check_versions:
            lines += ["### Reverse check", ""]
            lines += [f"- {k}: {v}" for k, v in sorted(self.check_versions.items())]
            lines += [f"- hits: {len(self.hits)}, kept: {len(self.kept)}, allowed: {len(self.allowed)}", ""]
        if self.hits:
            by_rule = Counter((h.rule.type, h.rule.value, h.rule.source) for h in self.hits)
            lines += ["| direct rule | source | foreign entries |", "|---|---|---|"]
            for (type_, value, source), n in by_rule.most_common(_MAX_LISTED):
                lines.append(f"| {type_}, {value} | {source} | {n} |")
            if len(by_rule) > _MAX_LISTED:
                lines.append(f"| ... {len(by_rule) - _MAX_LISTED} more rules | | |")
            lines.append("")
        return "\n".join(lines) + "\n"


def read_previous_counts(path: Path) -> dict[str, int] | None:
    """读取上一版 china.list 文件头记录的各数据源条目数；文件不存在时返回 None。"""
    if not path.is_file():
        return None
    counts: dict[str, int] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            if m := _UPSTREAM_HEADER_RE.match(line.rstrip("\n")):
                counts[m.group(1)] = int(m.group(2))
    return counts


def _merge(bundle: Bundle, upstream: Mapping[str, Upstream], report: BuildReport) -> tuple[Bundle, list[str]]:
    """手写规则在前，再按清单顺序接入上游数据；应用 [[exclude]] 并去重。"""
    excluded = {n.value for n in bundle.exclude}
    used_excludes: set[str] = set()
    rules = list(bundle.rules)
    seen = {(r.type, r.value) for r in rules}
    header: list[str] = []
    for spec in bundle.upstream:
        kind = spec.key
        if kind not in upstream:
            report.errors.append(f"{bundle.name}: no upstream data for {kind}")
            continue
        data = upstream[kind]
        added = 0
        bad = [(r, p) for r in data.rules if (p := value_error(r.type, r.value))]
        for rule, problem in bad[:_MAX_LISTED]:
            report.errors.append(f"{bundle.name}: {kind}: {rule.type}, {rule.value}: {problem}")
        if bad:
            continue
        for rule in data.rules:
            if rule.value in excluded:
                used_excludes.add(rule.value)
                continue
            if (rule.type, rule.value) not in seen:
                seen.add((rule.type, rule.value))
                rules.append(rule)
                added += 1
        report.sources[kind] = SourceStats(data.version, len(data.rules), added)
        for reason, values in data.skipped.items():
            report.skipped.setdefault(reason, []).extend(values)
        header.append(f"# upstream {kind}: {data.version} (entries: {len(data.rules)})")
    for value in sorted(excluded - used_excludes):
        report.warnings.append(f"{bundle.name}: [[exclude]] {value} matches no upstream entry")
    return dataclasses.replace(bundle, rules=tuple(rules)), header


def drop_covered(rules: Sequence[Rule]) -> tuple[list[Rule], int]:
    """去掉被同列表中更短的 host-suffix 覆盖的 host-suffix。

    同列表、同类型，模拟器下的去向不变；host 等其他类型优先级不同，保留不动。
    """
    suffixes = {r.value for r in rules if r.type == "host-suffix"}

    def covered(value: str) -> bool:
        labels = value.split(".")
        return any(".".join(labels[i:]) in suffixes for i in range(1, len(labels)))

    kept = [r for r in rules if r.type != "host-suffix" or not covered(r.value)]
    return kept, len(rules) - len(kept)


def _check_drop(previous: Mapping[str, int] | None, report: BuildReport) -> None:
    if previous is None:
        report.warnings.append("no previous china.list; upstream drop check skipped")
        return
    for kind, stats in report.sources.items():
        old = previous.get(kind)
        if old and stats.entries < old * MIN_RATIO:
            report.errors.append(f"{kind}: {stats.entries} entries, down from {old} in the previous release")


def _reverse_check(router: Router, bundles: Sequence[Bundle], data: CheckData, report: BuildReport) -> None:
    direct = [lst for lst in router.lists if lst.policy == DIRECT]
    hits = domain_hits(router, data.domains)
    hits += network_hits([r for lst in direct for r in lst.rules], data.networks)
    direct_bundles = [b for b in bundles if b.name in DIRECT_BUNDLES]
    # 上游规则的 source 即数据源的 key；allow_foreign 的数据源整体豁免
    allowed = {spec.key for b in direct_bundles for spec in b.upstream if spec.allow_foreign}
    report.allowed = [h for h in hits if h.rule.source in allowed]
    hits = [h for h in hits if h.rule.source not in allowed]
    keep = {n.value for b in direct_bundles for n in b.keep}
    report.kept = [h for h in hits if h.rule.value in keep]
    report.hits = [h for h in hits if h.rule.value not in keep]
    report.check_versions = dict(data.provenance)
    for value in sorted(keep - {h.rule.value for h in report.kept}):
        report.warnings.append(f"[[keep]] {value} matches no reverse-check hit")
    if report.hits:
        rules = len({(h.rule.type, h.rule.value) for h in report.hits})
        report.errors.append(
            f"reverse check: {len(report.hits)} foreign entries fall to direct through {rules} rules; "
            "add [[exclude]] or [[keep]] to china.toml"
        )
    if any(lst.name == PROTECTED_BUNDLE for lst in router.lists):
        for rule, zone in shadowed(router, PROTECTED_BUNDLE):
            report.errors.append(f"{rule.type}, {rule.value} ({rule.source}) routes {PROTECTED_BUNDLE} zone {zone.value} to direct")


def _check_samples(path: Path, router: Router, report: BuildReport) -> None:
    with path.open("rb") as fh:
        samples = tomllib.load(fh).get("sample", [])
    for sample in samples:
        host = sample.get("host")
        ip = ipaddress.ip_address(sample["ip"]) if "ip" in sample else None
        got = router.route(host, ip, final=FINAL)
        if got != sample["expect"]:
            report.errors.append(f"sample {host or sample.get('ip')}: expected {sample['expect']}, got {got}")


def build(
    bundles_dir: Path,
    out_dir: Path,
    *,
    upstream: Mapping[str, Upstream],
    check: CheckData,
    samples: Path | None,
    previous: Mapping[str, int] | None,
    owner: str,
    repo: str,
    static_files: Sequence[Path],
) -> BuildReport:
    report = BuildReport()
    report.errors += check_bundle_files(bundles_dir)
    bundles: list[Bundle] = []
    headers: dict[str, list[str]] = {}
    for bundle in load_bundles(bundles_dir):
        report.errors += validate_bundle(bundle)
        merged, header = _merge(bundle, upstream, report)
        rules, dropped = drop_covered(merged.rules)
        if dropped:
            merged = dataclasses.replace(merged, rules=tuple(rules))
            report.redundant[merged.name] = dropped
        bundles.append(merged)
        headers[merged.name] = header
    _check_drop(previous, report)
    lists = [RuleList(b.name, DIRECT if b.name in DIRECT_BUNDLES else b.name, b.rules) for b in bundles]
    router = Router(lists)
    _reverse_check(router, bundles, check, report)
    if samples is not None:
        _check_samples(samples, router, report)
    report.counts = {lst.name: len(lst.rules) for lst in lists}
    if report.errors:
        return report

    if out_dir.exists() and any(out_dir.iterdir()) and not (out_dir / OUTPUT_MARKER).exists():
        report.errors.append(f"refusing to replace {out_dir}: not empty and not a previous quanlight output")
        return report
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / OUTPUT_MARKER).write_text("", encoding="utf-8")
    for lst in lists:
        path = out_dir / f"{lst.name}.list"
        path.write_text(render_list(lst.name, lst.rules, headers[lst.name]), encoding="utf-8")
        report.sizes[lst.name] = path.stat().st_size
    readme = render_release_readme([b.name for b in bundles], DIRECT_BUNDLES, owner, repo)
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    for path in static_files:
        shutil.copy(path, out_dir / path.name)
    return report
