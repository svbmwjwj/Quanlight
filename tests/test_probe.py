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
    assert "host, www.example.com, direct" in local
    assert remote_policies(local) == ["reject"]


def test_probe_command_writes_all_files(tmp_path):
    from quanlight.cli import main

    assert main(["probe", "--out", str(tmp_path), "--base-url", "https://x"]) == 0
    assert (tmp_path / "probe-order.conf").is_file()
    assert "https://x/probe/probe-type-1.list" in (tmp_path / "probe-type.conf").read_text()
    assert len(list(tmp_path.glob("*.list"))) == 7
