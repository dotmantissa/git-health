from __future__ import annotations

import json
from dataclasses import dataclass

import git_health


@dataclass
class _Resp:
    status_code: int
    body: bytes


def _make_json_response(status_code: int, payload) -> _Resp:
    return _Resp(status_code=status_code, body=json.dumps(payload).encode("utf-8"))


def _run_with_router(repo_url: str, router) -> tuple[int, dict]:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    def fake_get(url: str):
        return router(url)

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.get = fake_get
    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    score = contract.analyze_repo(repo_url)
    details_raw = contract.get_details(repo_url)
    return score, json.loads(details_raw)


def test_nonexistent_repo_detected_from_repo_api_404() -> None:
    def router(url: str):
        if "api.github.com/repos/example/missing" in url:
            return _make_json_response(404, {"message": "Not Found"})
        return _Resp(status_code=500, body=b"")

    score, details = _run_with_router("https://github.com/example/missing", router)
    assert score == 0
    assert details["health_score"] == 0
    assert details["error"] == "repository not found"


def test_nonexistent_repo_detected_from_html_404_when_api_unavailable() -> None:
    def router(url: str):
        if "api.github.com/repos/example/missing" in url:
            return _make_json_response(500, {"message": "server error"})
        if "https://github.com/example/missing" == url:
            return _Resp(status_code=404, body=b"<html>Not Found</html>")
        return _Resp(status_code=500, body=b"")

    score, details = _run_with_router("https://github.com/example/missing", router)
    assert score == 0
    assert details["health_score"] == 0
    assert details["error"] == "repository not found"
    assert details["source"] == "html_status_404"


def test_existing_repo_not_false_positive_when_html_contains_404_token() -> None:
    repo_info = {
        "open_issues_count": 0,
        "license": {"key": "mit"},
        "fork": False,
        "archived": False,
        "disabled": False,
        "pushed_at": "2999-01-01T00:00:00Z",
    }
    commits = [{"commit": {"committer": {"date": "2999-01-01T00:00:00Z"}}}]

    def router(url: str):
        if "api.github.com/repos/example/repo/commits" in url:
            return _make_json_response(200, commits)
        if "api.github.com/repos/example/repo/readme" in url:
            return _make_json_response(200, {"name": "README.md"})
        if "api.github.com/repos/example/repo/contents/.github/workflows" in url:
            return _make_json_response(200, [{"name": "ci.yml"}])
        if "api.github.com/repos/example/repo/contents/" in url:
            return _make_json_response(200, [{"name": ".github"}])
        if "api.github.com/repos/example/repo" in url:
            return _make_json_response(200, repo_info)
        if "https://github.com/example/repo" == url:
            html = """
            <html><body>
            Build number 4042
            README
            .github/workflows
            <relative-time datetime=\"2999-01-01T00:00:00Z\"></relative-time>
            </body></html>
            """
            return _Resp(status_code=200, body=html.encode("utf-8"))
        return _Resp(status_code=500, body=b"")

    score, details = _run_with_router("https://github.com/example/repo", router)
    assert score == 100
    assert details["health_score"] == 100
    assert details["source"] == "api_plus_html"


def test_api_plus_html_merge_fills_missing_trust_signals() -> None:
    repo_info = {
        "open_issues_count": 31,
        "license": None,
        "fork": False,
        "archived": False,
        "disabled": False,
        "pushed_at": None,
    }

    def router(url: str):
        if "api.github.com/repos/example/repo/commits" in url:
            return _make_json_response(200, [])
        if "api.github.com/repos/example/repo/readme" in url:
            return _make_json_response(404, {"message": "Not Found"})
        if "api.github.com/repos/example/repo/contents/.github/workflows" in url:
            return _make_json_response(404, {"message": "Not Found"})
        if "api.github.com/repos/example/repo/contents/" in url:
            return _make_json_response(200, [{"name": "src"}])
        if "api.github.com/repos/example/repo" in url:
            return _make_json_response(200, repo_info)
        if "https://github.com/example/repo" == url:
            html = """
            README
            View license
            .github/workflows
            <relative-time datetime=\"2999-01-01T00:00:00Z\"></relative-time>
            Issues <span class=\"Counter\">31</span>
            """
            return _Resp(status_code=200, body=html.encode("utf-8"))
        return _Resp(status_code=500, body=b"")

    score, details = _run_with_router("https://github.com/example/repo", router)
    assert score == 97
    assert details["has_readme"] is True
    assert details["has_ci"] is True
    assert details["has_license"] is True
    assert details["issue_penalty"] == 3


def test_html_only_path_scores_with_signal_parsing() -> None:
    def router(url: str):
        if "api.github.com/repos/example/repo" in url:
            return _make_json_response(500, {"message": "error"})
        if "https://github.com/example/repo" == url:
            html = """
            README
            View license
            .github/workflows
            Issues <span class=\"Counter\">35</span>
            <relative-time datetime=\"2999-01-01T00:00:00Z\"></relative-time>
            """
            return _Resp(status_code=200, body=html.encode("utf-8"))
        return _Resp(status_code=500, body=b"")

    score, details = _run_with_router("https://github.com/example/repo", router)
    assert score == 97
    assert details["source"] == "html_only"
    assert details["issue_penalty"] == 3


def test_all_sources_fail_uses_cached_score() -> None:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}
    repo_url = "https://github.com/example/repo"

    def ok_router(url: str):
        if "api.github.com/repos/example/repo/commits" in url:
            return _make_json_response(200, [{"commit": {"committer": {"date": "2999-01-01T00:00:00Z"}}}])
        if "api.github.com/repos/example/repo/readme" in url:
            return _make_json_response(200, {"name": "README.md"})
        if "api.github.com/repos/example/repo/contents/.github/workflows" in url:
            return _make_json_response(200, [{"name": "ci.yml"}])
        if "api.github.com/repos/example/repo/contents/" in url:
            return _make_json_response(200, [{"name": ".github"}])
        if "api.github.com/repos/example/repo" in url:
            return _make_json_response(
                200,
                {
                    "open_issues_count": 0,
                    "license": {"key": "mit"},
                    "fork": False,
                    "archived": False,
                    "disabled": False,
                    "pushed_at": "2999-01-01T00:00:00Z",
                },
            )
        if "https://github.com/example/repo" == url:
            return _Resp(status_code=200, body=b"README")
        return _Resp(status_code=500, body=b"")

    def failing_router(_url: str):
        return _Resp(status_code=500, body=b"")

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    git_health.gl.nondet.web.get = ok_router
    first_score = contract.analyze_repo(repo_url)
    assert first_score == 100

    git_health.gl.nondet.web.get = failing_router
    second_score = contract.analyze_repo(repo_url)

    assert second_score == 100
    details = json.loads(contract.get_details(repo_url))
    assert details["used_cached_score"] is True


def test_invalid_url_is_stored_as_zero() -> None:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    score = contract.analyze_repo("https://notgithub.com/foo/bar")
    assert score == 0
    assert contract.get_score("https://notgithub.com/foo/bar") == 0
    details = json.loads(contract.get_details("https://notgithub.com/foo/bar"))
    assert "invalid repo url" in details["error"]


def test_url_normalization_supports_git_suffix_and_tree_paths() -> None:
    repo_info = {
        "open_issues_count": 0,
        "license": {"key": "mit"},
        "fork": False,
        "archived": False,
        "disabled": False,
        "pushed_at": "2999-01-01T00:00:00Z",
    }

    def router(url: str):
        if "api.github.com/repos/example/repo/commits" in url:
            return _make_json_response(200, [{"commit": {"committer": {"date": "2999-01-01T00:00:00Z"}}}])
        if "api.github.com/repos/example/repo/readme" in url:
            return _make_json_response(200, {"name": "README.md"})
        if "api.github.com/repos/example/repo/contents/.github/workflows" in url:
            return _make_json_response(200, [{"name": "ci.yml"}])
        if "api.github.com/repos/example/repo/contents/" in url:
            return _make_json_response(200, [{"name": ".github"}])
        if "api.github.com/repos/example/repo" in url:
            return _make_json_response(200, repo_info)
        if "https://github.com/example/repo" == url:
            return _Resp(status_code=200, body=b"README")
        return _Resp(status_code=500, body=b"")

    input_url = "https://github.com/example/repo.git/tree/main?tab=readme"
    score, details = _run_with_router(input_url, router)

    assert score == 100
    assert details["canonical_repo_url"] == "https://github.com/example/repo"
