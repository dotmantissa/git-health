from __future__ import annotations

import json

import git_health


def _run_with_payloads(repo_payload: dict, readme_payload, workflows_payload) -> tuple[int, dict]:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    def fake_render(url: str, mode: str = "text") -> str:
        assert mode == "text"
        if url.endswith("/repos/example/repo"):
            return json.dumps(repo_payload)
        if url.endswith("/repos/example/repo/readme"):
            return json.dumps(readme_payload)
        if url.endswith("/repos/example/repo/contents/.github/workflows"):
            return json.dumps(workflows_payload)
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
        "pushed_at": "2999-01-01T00:00:00Z",
        "open_issues_count": 0,
        "size": 0,
        "license": {"key": "mit"},
        "fork": True,
    }

    score, details = _run_with_payloads(
        repo_payload=repo,
        readme_payload={"name": "README.md"},
        workflows_payload=[{"name": "ci.yml"}],
    )

    assert score == 75
    assert details["empty_penalty"] == 20
    assert details["is_fork"] is True


def test_get_details_unknown_repo_returns_empty_json() -> None:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}
    assert contract.get_details("https://github.com/unknown/repo") == "{}"
