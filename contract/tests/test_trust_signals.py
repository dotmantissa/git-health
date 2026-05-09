from __future__ import annotations

import json

import git_health


def _run_analysis(
    repo_payload: dict,
    commits_payload,
    readme_payload,
    root_contents_payload,
    workflows_payload,
) -> tuple[int, dict]:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    def fake_render(url: str, mode: str = "text") -> str:
        assert mode == "text"
        if url.endswith("/repos/example/repo"):
            return json.dumps(repo_payload)
        if url.endswith("/repos/example/repo/commits?per_page=1"):
            return json.dumps(commits_payload)
        if url.endswith("/repos/example/repo/readme"):
            return json.dumps(readme_payload)
        if url.endswith("/repos/example/repo/contents/"):
            return json.dumps(root_contents_payload)
        if url.endswith("/repos/example/repo/contents/.github/workflows"):
            return json.dumps(workflows_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.render = fake_render
    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    score = contract.analyze_repo("https://github.com/example/repo")
    details = json.loads(contract.get_details("https://github.com/example/repo"))
    return score, details


def test_trust_signals_all_present_no_penalty() -> None:
    repo = {
        "open_issues_count": 0,
        "license": {"key": "mit"},
        "fork": False,
    }
    score, details = _run_analysis(
        repo_payload=repo,
        commits_payload=[{"commit": {"committer": {"date": "2999-01-01T00:00:00Z"}}}],
        readme_payload={"name": "README.md"},
        root_contents_payload=[{"name": ".github"}],
        workflows_payload=[{"name": "ci.yml"}],
    )
    assert score == 100
    assert details["has_readme"] is True
    assert details["has_ci"] is True
    assert details["has_license"] is True


def test_missing_single_trust_signal_deducts_five() -> None:
    repo = {
        "open_issues_count": 0,
        "license": {"key": "mit"},
        "fork": False,
    }
    score, _ = _run_analysis(
        repo_payload=repo,
        commits_payload=[{"commit": {"committer": {"date": "2999-01-01T00:00:00Z"}}}],
        readme_payload={"message": "Not Found"},
        root_contents_payload=[{"name": ".github"}],
        workflows_payload=[{"name": "ci.yml"}],
    )
    assert score == 95


def test_missing_all_trust_signals_deducts_fifteen() -> None:
    repo = {
        "open_issues_count": 0,
        "license": None,
        "fork": False,
    }
    score, _ = _run_analysis(
        repo_payload=repo,
        commits_payload=[{"commit": {"committer": {"date": "2999-01-01T00:00:00Z"}}}],
        readme_payload={"message": "Not Found"},
        root_contents_payload=[],
        workflows_payload={"message": "Not Found"},
    )
    assert score == 85


def test_trust_signal_penalties_stack_with_issue_penalty() -> None:
    repo = {
        "open_issues_count": 35,  # issue penalty = 3
        "license": None,
        "fork": False,
    }
    score, details = _run_analysis(
        repo_payload=repo,
        commits_payload=[{"commit": {"committer": {"date": "2999-01-01T00:00:00Z"}}}],
        readme_payload={"message": "Not Found"},
        root_contents_payload=[],
        workflows_payload={"message": "Not Found"},
    )
    assert score == 82
    assert details["issue_penalty"] == 3
    assert details["health_score"] == 82
