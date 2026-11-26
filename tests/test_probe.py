from quanlight.emit import PROBE_CASES, render_probe


def test_probe_cases_cover_the_open_questions():
    assert set(PROBE_CASES) == {"order", "type", "local", "wildcard", "cname"}


def test_probe_outputs():
    for case in PROBE_CASES:
        files = render_probe(case, "https://cdn.example/q@release/probe")
        lists = {k: v for k, v in files.items() if k.endswith(".list")}
        snippet = files[f"probe-{case}.conf"]
        assert lists, case
        for name in lists:
            assert f"/probe/{name}," in snippet
        assert "force-policy=reject" in snippet


def remote_policies(snippet: str) -> list[str]:
    return [l.split("force-policy=")[1].split(",")[0] for l in snippet.splitlines() if "/probe/" in l]


def test_probe_conflict_cases_pair_reject_with_direct():
    for case in ("order", "type"):
        snippet = render_probe(case, "https://x/probe")[f"probe-{case}.conf"]
        assert remote_policies(snippet) == ["reject", "direct"]
    local = render_probe("local", "https://x/probe")["probe-local.conf"]
    assert "host, www.example.net, direct" in local
    assert remote_policies(local) == ["reject"]


def test_probe_command_writes_all_files(tmp_path):
    from quanlight.cli import main

    assert main(["probe", "--out", str(tmp_path), "--base-url", "https://x"]) == 0
    assert (tmp_path / "probe-order.conf").is_file()
    assert "https://x/probe/probe-type-1.list" in (tmp_path / "probe-type.conf").read_text()
    assert len(list(tmp_path.glob("*.list"))) == 14


def test_probe_profile_serves_lists_from_local_backend():
    from quanlight.emit import PROBE_CASES, render_probe_profile

    files = render_probe_profile()
    profile = files["quanlight-probe.conf"]
    script = files["quanlight-probe.js"]
    assert "[http_backend]\nquanlight-probe.js, tag=quanlight-probe, path=^/quanlight-probe/, enabled=true" in profile
    assert "http://127.0.0.1:9999/quanlight-probe/order-1.list, tag=order-1, force-policy=reject" in profile
    assert "final, direct" in profile and "host, www.example.net, direct" in profile
    assert "[server_local]" in profile and "server=" not in profile
    assert '"order-1.list": "host-suffix, example.com, order-1\\n"' in script
    assert "$done(" in script


def test_probe_cases_use_distinct_hosts():
    from quanlight.emit import PROBE_CASES

    first_hosts = [visit[0] for _, _, visit in PROBE_CASES.values()]
    assert len(set(first_hosts)) == len(first_hosts)


def test_probe_profile_can_reference_script_by_url():
    from quanlight.emit import render_probe_profile

    profile = render_probe_profile("https://x/probe/quanlight-probe.js")["quanlight-probe.conf"]
    assert "https://x/probe/quanlight-probe.js, tag=quanlight-probe, path=^/quanlight-probe/" in profile


def test_probe_profile_remote_mode_lists_files_without_backend():
    from quanlight.emit import render_probe_profile

    files = render_probe_profile(remote_base="https://m/probe")
    profile = files["quanlight-probe.conf"]
    assert "https://m/probe/order-1.list, tag=order-1, force-policy=reject" in profile
    assert "127.0.0.1" not in profile and "quanlight-probe.js" not in profile
    assert files["order-1.list"] == "host-suffix, example.com, order-1\n"
