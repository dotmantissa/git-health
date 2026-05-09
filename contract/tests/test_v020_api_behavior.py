from __future__ import annotations

import json
from dataclasses import dataclass

import git_health


@dataclass
class _Resp:
    status_code: int
    body: bytes


def _http(payload, status_code: int = 200) -> _Resp:
    return _Resp(status_code=status_code, body=json.dumps(payload).encode("utf-8"))


def _run_with_payloads(
    repo_payload: dict,
    commits_payload,
    readme_payload,
    root_contents_payload,
    workflows_payload,
) -> tuple[int, dict]:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    def fake_get(url: str):
        if url.endswith("/repos/example/repo"):
            return _http(repo_payload)
        if url.endswith("/repos/example/repo/commits?per_page=1"):
            if commits_payload == "__empty_409__":
                return _Resp(status_code=409, body=b'{"message":"Git Repository is empty."}')
            return _http(commits_payload)
        if url.endswith("/repos/example/repo/readme"):
            if isinstance(readme_payload, dict) and "message" in readme_payload:
                return _http(readme_payload, status_code=404)
            return _http(readme_payload)
        if url.endswith("/repos/example/repo/contents/"):
            return _http(root_contents_payload)
        if url.endswith("/repos/example/repo/contents/.github/workflows"):
            if isinstance(workflows_payload, dict) and "message" in workflows_payload:
                return _http(workflows_payload, status_code=404)
            return _http(workflows_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.get = fake_get
    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    score = contract.analyze_repo("https://github.com/example/repo")
    details_raw = contract.get_details("https://github.com/example/repo")
    return score, json.loads(details_raw)


def test_repo_not_found_returns_zero_and_error_payload() -> None:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    def fake_get(url: str):
        if url.endswith("/repos/example/repo"):
            return _http({"message": "Not Found"}, status_code=404)
        raise AssertionError(f"Unexpected URL: {url}")

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.get = fake_get
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
        root_contents_payload=[],
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
        root_contents_payload=[{"name": ".travis.yml"}],
        workflows_payload={"message": "Not Found"},
    )

    assert score == 100
    assert details["has_ci"] is True


def test_empty_repo_message_on_commits_is_treated_as_zero_commits() -> None:
    repo = {
        "open_issues_count": 0,
        "license": {"key": "mit"},
        "fork": False,
    }
    score, details = _run_with_payloads(
        repo_payload=repo,
        commits_payload="__empty_409__",
        readme_payload={"name": "README.md"},
        root_contents_payload=[{"name": ".github"}],
        workflows_payload={"message": "Not Found"},
    )
    assert score == 15
    assert details["is_empty"] is True


def test_get_details_unknown_repo_returns_empty_json() -> None:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}
    assert contract.get_details("https://github.com/unknown/repo") == "{}"
