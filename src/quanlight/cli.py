"""命令行入口：build 与 probe。"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

from . import fetch
from .build import CheckData, Upstream, build, read_previous_counts
from .emit import PROBE_CASES, render_probe, render_probe_profile
from .manifest import ManifestError, load_bundles
from .model import Rule, UpstreamSpec
from .sources import (
    CHINA_IP_REPO,
    DNSMASQ_APPLE_REPO,
    GITHUB_META_URL,
    GOOGLE_IPRANGES_URL,
    TELEGRAM_CIDR_URL,
    V2FLY_REPO,
    SourceError,
    parse_cidr_list,
    parse_dnsmasq,
    parse_github_meta,
    parse_google_ipranges,
    parse_telegram_cidr,
)
from .v2fly import V2flyError, expand, foreign_domains, import_direct

DEFAULT_OWNER = "svbmwjwj"
DEFAULT_REPO = "quanlight"
DEFAULT_BASE_URL = f"https://raw.githubusercontent.com/{DEFAULT_OWNER}/{DEFAULT_REPO}/release"
FOREIGN_DATA_FILE = "geolocation-!cn"


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()[:16]


def _ip_rules(text: str, what: str, source: str) -> list[Rule]:
    return [
        Rule(type="ip-cidr" if n.version == 4 else "ip6-cidr", value=str(n), source=source)
        for n in dict.fromkeys(parse_cidr_list(text, what))
    ]


def _sync_upstream(specs: list[UpstreamSpec], v2fly_dir: Path, v2fly_version: str) -> dict[str, Upstream]:
    """下载并解析清单声明的直连数据源，键为 UpstreamSpec.key。"""
    out: dict[str, Upstream] = {}
    for spec in specs:
        if spec.key in out:
            continue
        if spec.kind == "v2fly" and spec.file:
            result = import_direct(expand(v2fly_dir, spec.file), source=f"v2fly:{spec.file}")
            skipped: dict[str, list[str]] = {}
            for entry, reason in result.skipped:
                skipped.setdefault(reason, []).append(entry.value)
            out[spec.key] = Upstream(spec.key, v2fly_version, result.rules, skipped)
        elif spec.kind == "dnsmasq-apple-china":
            text = fetch.fetch_text(DNSMASQ_APPLE_REPO["url"])
            rules = [Rule("host-suffix", d, spec.key) for d in parse_dnsmasq(text)]
            version = fetch.fetch_commit(DNSMASQ_APPLE_REPO["repo"], DNSMASQ_APPLE_REPO["branch"])
            out[spec.key] = Upstream(spec.key, version, rules)
        elif spec.kind == "china-operator-ip":
            rules = _ip_rules(fetch.fetch_text(CHINA_IP_REPO["v4"]), "china-operator-ip v4", spec.key)
            rules += _ip_rules(fetch.fetch_text(CHINA_IP_REPO["v6"]), "china-operator-ip v6", spec.key)
            version = fetch.fetch_commit(CHINA_IP_REPO["repo"], CHINA_IP_REPO["branch"])
            out[spec.key] = Upstream(spec.key, version, rules)
    return out


def _load_check_data(v2fly_dir: Path, v2fly_version: str) -> CheckData:
    """反向检查数据：只用于检查，不进入列表。"""
    telegram = fetch.fetch_text(TELEGRAM_CIDR_URL)
    github = fetch.fetch_text(GITHUB_META_URL)
    google = fetch.fetch_text(GOOGLE_IPRANGES_URL)
    return CheckData(
        domains={f"v2fly {FOREIGN_DATA_FILE}": foreign_domains(expand(v2fly_dir, FOREIGN_DATA_FILE))},
        networks={
            "telegram-cidr": parse_telegram_cidr(telegram),
            "github-meta": parse_github_meta(github),
            "google-ipranges": parse_google_ipranges(google),
        },
        provenance={
            f"v2fly {FOREIGN_DATA_FILE}": v2fly_version,
            "telegram-cidr": _digest(telegram),
            "github-meta": _digest(github),
            "google-ipranges": _digest(google),
        },
    )


def _cmd_build(args: argparse.Namespace) -> int:
    try:
        specs = [spec for b in load_bundles(args.bundles) for spec in b.upstream]
        v2fly_dir = fetch.fetch_v2fly_data(args.cache / "v2fly", V2FLY_REPO["url"])
        v2fly_version = fetch.fetch_commit(V2FLY_REPO["repo"], V2FLY_REPO["branch"])
        upstream = _sync_upstream(specs, v2fly_dir, v2fly_version)
        data = _load_check_data(v2fly_dir, v2fly_version)
    except (fetch.FetchError, SourceError, V2flyError, ManifestError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    root = args.bundles.resolve().parent
    report = build(
        args.bundles,
        args.out,
        upstream=upstream,
        check=data,
        samples=args.samples,
        previous=read_previous_counts(args.previous / "china.list") if args.previous else None,
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


def _cmd_probe(args: argparse.Namespace) -> int:
    args.out.mkdir(parents=True, exist_ok=True)
    for case in PROBE_CASES:
        for name, text in render_probe(case, args.base_url.rstrip("/") + "/probe").items():
            (args.out / name).write_text(text, encoding="utf-8")
    for name, text in render_probe_profile(remote_base=args.base_url.rstrip("/") + "/probe").items():
        (args.out / name).write_text(text, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quanlight")
    parser.add_argument("--cache", type=Path, default=Path(".cache"))
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="sync direct data, run checks and write filter lists")
    p_build.add_argument("--bundles", type=Path, default=Path("bundles"))
    p_build.add_argument("--out", type=Path, default=Path("dist"))
    p_build.add_argument("--samples", type=Path, default=Path("tests/samples.toml"))
    p_build.add_argument("--previous", type=Path, help="previous release directory, for the upstream drop check")
    p_build.add_argument("--owner", default=DEFAULT_OWNER)
    p_build.add_argument("--repo", default=DEFAULT_REPO)
    p_build.set_defaults(func=_cmd_build)

    p_probe = sub.add_parser("probe", help="write rule-matching probe lists")
    p_probe.add_argument("--out", type=Path, default=Path("dist/probe"))
    p_probe.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p_probe.set_defaults(func=_cmd_probe)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
