from __future__ import annotations

import json

import git_health


def _run_with_payloads(
    repo_payload: dict,
    commits_payload,
    readme_payload,
    workflows_payload,
    ci_file_payloads: dict[str, object] | None = None,
) -> tuple[int, dict]:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}
    ci_file_payloads = ci_file_payloads or {}

    def fake_render(url: str, mode: str = "text") -> str:
        assert mode == "text"
        if url.endswith("/repos/example/repo"):
            return json.dumps(repo_payload)
        if url.endswith("/repos/example/repo/commits?per_page=1"):
            return json.dumps(commits_payload)
        if url.endswith("/repos/example/repo/readme"):
            return json.dumps(readme_payload)
        if url.endswith("/repos/example/repo/contents/.github/workflows"):
            return json.dumps(workflows_payload)
        for path, payload in ci_file_payloads.items():
            if url.endswith(path):
                return json.dumps(payload)
        raise AssertionError(f"Unexpected URL: {url}")

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.render = fake_render
    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    score = contract.analyze_repo("https://github.com/example/repo")
    details_raw = contract.get_details("https://github.com/example/repo")
    return score, json.loads(details_raw)


def test_repo_not_found_returns_zero_and_error_payload() -> None:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    def fake_render(url: str, mode: str = "text") -> str:
        assert mode == "text"
        if url.endswith("/repos/example/repo"):
            return json.dumps({"message": "Not Found"})
        raise AssertionError(f"Unexpected URL: {url}")

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.render = fake_render
    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    score = contract.analyze_repo("https://github.com/example/repo")
    details = json.loads(contract.get_details("https://github.com/example/repo"))

    assert score == 0
    assert details["health_score"] == 0
    assert "error" in details


def test_empty_and_fork_penalties_are_applied() -> None:
    repo = {
        "open_issues_count": 0,
        "license": {"key": "mit"},
        "fork": True,
    }

    score, details = _run_with_payloads(
        repo_payload=repo,
        commits_payload=[],
        readme_payload={"name": "README.md"},
        workflows_payload=[{"name": "ci.yml"}],
    )

    assert score == 10
    assert details["empty_penalty"] == 20
    assert details["is_fork"] is True


def test_ci_fallback_file_counts_as_ci_present() -> None:
    repo = {
        "open_issues_count": 0,
        "license": {"key": "mit"},
        "fork": False,
    }

    score, details = _run_with_payloads(
        repo_payload=repo,
        commits_payload=[{"commit": {"committer": {"date": "2999-01-01T00:00:00Z"}}}],
        readme_payload={"name": "README.md"},
        workflows_payload={"message": "Not Found"},
        ci_file_payloads={
            "/repos/example/repo/contents/.travis.yml": {"name": ".travis.yml"},
        },
    )

    assert score == 100
    assert details["has_ci"] is True


def test_get_details_unknown_repo_returns_empty_json() -> None:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}
    assert contract.get_details("https://github.com/unknown/repo") == "{}"
