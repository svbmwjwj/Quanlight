"""命令行入口：build、import-v2fly、diff-v2fly 与 probe。"""

import argparse
import dataclasses
import hashlib
import ipaddress
import os
import shutil
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import fetch
from .check import build_ios_lists, cross_check, direct_exceptions, find_misfires
from .emit import PROBE_CASES, render_list, render_probe, render_release_readme
from .manifest import check_bundle_files, dump_bundle, load_bundles, validate_bundle
from .match import IPNetwork, route
from .model import Bundle, Rule
from .sources import (
    CHECK_SOURCES,
    UPSTREAM_KINDS,
    SourceError,
    parse_cidr_list,
    parse_dnsmasq,
    parse_telegram_cidr,
)
from .v2fly import diff, expand, to_rules

OUTPUT_MARKER = ".quanlight-dist"  # 标记本工具可以整体替换的输出目录
DEFAULT_OWNER = "svbmwjwj"
DEFAULT_REPO = "quanlight"
DEFAULT_BASE_URL = f"https://raw.githubusercontent.com/{DEFAULT_OWNER}/{DEFAULT_REPO}/release"
UPSTREAM_PARSERS: dict[str, Callable[[str, str], list[Rule]]] = {"telegram-cidr": parse_telegram_cidr}


@dataclass
class CheckData:
    cn_domains: set[str]
    cn_networks: list[IPNetwork]
    provenance: dict[str, str]


@dataclass
class BuildReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    broad: list[tuple[str, Rule]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = ["## quanlight build", "", f"Result: {'FAILED' if self.errors else 'OK'}", ""]
        if self.errors:
            lines += ["### Errors", ""] + [f"- {e}" for e in self.errors] + [""]
        if self.counts:
            lines += ["### Lists", "", "| list | rules |", "|---|---|"]
            lines += [f"| {k} | {v} |" for k, v in self.counts.items()] + [""]
        if self.broad:
            lines += ["### Broad rules", ""]
            lines += [f"- {b}: {r.type}, {r.value} (review by {r.review_by})" for b, r in self.broad] + [""]
        if self.provenance:
            lines += ["### Data versions", ""] + [f"- {k}: {v}" for k, v in sorted(self.provenance.items())]
        return "\n".join(lines) + "\n"


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()[:16]


def _merge_upstream(bundle: Bundle, upstream: Mapping[str, str], report: BuildReport) -> tuple[Bundle, dict[str, str]]:
    rules = list(bundle.rules)
    seen = {(r.type, r.value) for r in rules}
    used: dict[str, str] = {}
    for kind in bundle.upstream:
        if kind not in UPSTREAM_PARSERS or kind not in upstream:
            report.errors.append(f"{bundle.name}: no upstream data for {kind}")
            continue
        try:
            parsed = UPSTREAM_PARSERS[kind](upstream[kind], bundle.name)
        except SourceError as exc:
            report.errors.append(f"{bundle.name}: {kind}: {exc}")
            continue
        used[kind] = _digest(upstream[kind])
        for rule in parsed:
            if (rule.type, rule.value) not in seen:
                seen.add((rule.type, rule.value))
                rules.append(rule)
    return dataclasses.replace(bundle, rules=tuple(rules)), used


def _check_samples(path: Path, lists, report: BuildReport) -> None:
    with path.open("rb") as fh:
        samples = tomllib.load(fh).get("sample", [])
    for sample in samples:
        host = sample.get("host")
        ip = ipaddress.ip_address(sample["ip"]) if "ip" in sample else None
        got = route(lists, host, ip, final="direct")
        if got != sample["expect"]:
            report.errors.append(f"sample {host or sample.get('ip')}: expected {sample['expect']}, got {got}")


def build(
    bundles_dir: Path,
    out_dir: Path,
    *,
    today: date,
    data: CheckData,
    upstream: Mapping[str, str],
    samples: Path | None,
    owner: str,
    repo: str,
    static_files: Sequence[Path],
) -> BuildReport:
    report = BuildReport(provenance=dict(data.provenance))
    report.errors += check_bundle_files(bundles_dir)
    bundles: list[Bundle] = []
    list_provenance: dict[str, dict[str, str]] = {}
    for bundle in load_bundles(bundles_dir):
        report.errors += validate_bundle(bundle, today)
        merged, used = _merge_upstream(bundle, upstream, report)
        bundles.append(merged)
        list_provenance[merged.name] = used
        report.provenance.update(used)
        report.broad += [(merged.name, r) for r in merged.rules if r.breadth == "broad"]
    exceptions = direct_exceptions(bundles)
    lists = build_ios_lists(bundles, exceptions)
    report.errors += cross_check(bundles)
    for m in find_misfires(lists, data.cn_domains, data.cn_networks):
        report.errors.append(f"misfire: {m.bundle} ({m.rule.type}, {m.rule.value}) routes mainland {m.target} to proxy")
    if samples is not None:
        _check_samples(samples, lists, report)
    report.counts = {lst.name: len({(r.type, r.value) for r in lst.rules}) for lst in lists}
    if report.errors:
        return report

    if out_dir.exists() and any(out_dir.iterdir()) and not (out_dir / OUTPUT_MARKER).exists():
        report.errors.append(f"refusing to replace {out_dir}: not empty and not a previous quanlight output")
        return report
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "ios").mkdir(parents=True)
    (out_dir / OUTPUT_MARKER).write_text("", encoding="utf-8")
    for lst in lists:
        text = render_list(lst.name, lst.rules, list_provenance.get(lst.name, {}))
        (out_dir / "ios" / f"{lst.name}.list").write_text(text, encoding="utf-8")
    readme = render_release_readme(bundles, owner, repo)
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    for path in static_files:
        shutil.copy(path, out_dir / path.name)
    return report


def _load_check_data(cache: Path) -> CheckData:
    texts = {k: fetch.fetch_text(v["url"]) for k, v in CHECK_SOURCES.items() if k != "v2fly"}
    domains = parse_dnsmasq(texts["dnsmasq-china-list"])
    v2fly_dir = fetch.fetch_v2fly_data(cache / "v2fly", CHECK_SOURCES["v2fly"]["url"])
    domains |= {e.value for e in expand(v2fly_dir, "geolocation-cn") if e.kind in ("domain", "full") and "ads" not in e.attrs}
    networks = parse_cidr_list(texts["china-operator-ip-v4"]) + parse_cidr_list(texts["china-operator-ip-v6"])
    provenance = {k: fetch.fetch_commit(v["repo"], v["branch"]) for k, v in CHECK_SOURCES.items()}
    return CheckData(cn_domains=domains, cn_networks=networks, provenance=provenance)


def _cmd_build(args: argparse.Namespace) -> int:
    bundles = load_bundles(args.bundles)
    kinds = {kind for b in bundles for kind in b.upstream}
    try:
        upstream = {kind: fetch.fetch_text(UPSTREAM_KINDS[kind]) for kind in kinds if kind in UPSTREAM_KINDS}
        data = _load_check_data(args.cache)
    except (fetch.FetchError, SourceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    root = args.bundles.resolve().parent
    report = build(
        args.bundles,
        args.out,
        today=date.today(),
        data=data,
        upstream=upstream,
        samples=args.samples,
        owner=args.owner,
        repo=args.repo,
        static_files=[p for p in (root / "LICENSE", root / "NOTICE") if p.is_file()],
    )
    markdown = report.to_markdown()
    print(markdown)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(markdown)
    return 1 if report.errors else 0


def _v2fly_dir(args: argparse.Namespace) -> Path:
    if args.v2fly_data:
        return args.v2fly_data
    return fetch.fetch_v2fly_data(args.cache / "v2fly", CHECK_SOURCES["v2fly"]["url"])


def _cmd_import(args: argparse.Namespace) -> int:
    result = to_rules(expand(_v2fly_dir(args), args.file, exclude=args.exclude), source=f"v2fly:{args.file}")
    bundle = Bundle(
        name=args.bundle,
        description=f"Imported from v2fly {args.file}; review every rule type",
        order=args.order,
        rules=tuple(result.rules),
        v2fly_exclude=tuple(args.exclude),
    )
    print(dump_bundle(bundle), end="")
    for entry, reason in result.skipped:
        print(f"skipped {entry.kind}:{entry.value} ({entry.file}): {reason}", file=sys.stderr)
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    data_dir = _v2fly_dir(args)
    rows: list[str] = []
    for bundle in load_bundles(args.bundles):
        files = sorted({r.source.removeprefix("v2fly:") for r in bundle.rules if r.source.startswith("v2fly:")})
        for name in files:
            imported = to_rules(expand(data_dir, name, exclude=bundle.v2fly_exclude), source=f"v2fly:{name}")
            scoped = dataclasses.replace(bundle, rules=tuple(r for r in bundle.rules if r.source == f"v2fly:{name}"))
            added, removed = diff(scoped, imported)
            rows += [f"| {bundle.name} | added | {r.type}, {r.value} |" for r in added]
            rows += [f"| {bundle.name} | removed | {r.type}, {r.value} |" for r in removed]
    lines = ["## v2fly upstream diff", ""]
    lines += ["| bundle | change | rule |", "|---|---|---|", *rows] if rows else ["No changes."]
    print("\n".join(lines))
    return 0


def _cmd_probe(args: argparse.Namespace) -> int:
    args.out.mkdir(parents=True, exist_ok=True)
    for case in PROBE_CASES:
        for name, text in render_probe(case, args.base_url.rstrip("/") + "/probe").items():
            (args.out / name).write_text(text, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quanlight")
    parser.add_argument("--cache", type=Path, default=Path(".cache"))
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="check bundles and write filter lists")
    p_build.add_argument("--bundles", type=Path, default=Path("bundles"))
    p_build.add_argument("--out", type=Path, default=Path("dist"))
    p_build.add_argument("--samples", type=Path, default=Path("tests/samples.toml"))
    p_build.add_argument("--owner", default=DEFAULT_OWNER)
    p_build.add_argument("--repo", default=DEFAULT_REPO)
    p_build.set_defaults(func=_cmd_build)

    p_import = sub.add_parser("import-v2fly", help="draft a bundle manifest from a v2fly data file")
    p_import.add_argument("file")
    p_import.add_argument("--bundle", required=True)
    p_import.add_argument("--order", type=int, default=50)
    p_import.add_argument("--exclude", action="append", default=[])
    p_import.add_argument("--v2fly-data", type=Path)
    p_import.set_defaults(func=_cmd_import)

    p_diff = sub.add_parser("diff-v2fly", help="report v2fly changes against bundle manifests")
    p_diff.add_argument("--bundles", type=Path, default=Path("bundles"))
    p_diff.add_argument("--v2fly-data", type=Path)
    p_diff.set_defaults(func=_cmd_diff)

    p_probe = sub.add_parser("probe", help="write rule-matching probe lists")
    p_probe.add_argument("--out", type=Path, default=Path("dist/probe"))
    p_probe.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p_probe.set_defaults(func=_cmd_probe)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
