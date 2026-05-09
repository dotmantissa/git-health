from __future__ import annotations

import json
from dataclasses import dataclass

import git_health


@dataclass
class _Resp:
    status_code: int
    body: bytes


def _run_with_html(html: str, status_code: int = 200) -> tuple[int, dict]:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    def fake_get(_url: str):
        return _Resp(status_code=status_code, body=html.encode("utf-8"))

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.get = fake_get
    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    score = contract.analyze_repo("https://github.com/example/repo")
    details_raw = contract.get_details("https://github.com/example/repo")
    return score, json.loads(details_raw)


def test_repo_not_found_returns_zero_and_error_payload() -> None:
    score, details = _run_with_html("", status_code=404)
    assert score == 0
    assert details["health_score"] == 0
    assert "error" in details


def test_repo_not_found_html_status_returns_zero() -> None:
    html = """
    <html>
      <head>
        <title>Page not found · GitHub</title>
      </head>
      <body>
        <h1>Page not found</h1>
      </body>
    </html>
    """
    score, details = _run_with_html(html, status_code=404)
    assert score == 0
    assert details["health_score"] == 0
    assert "not found" in details["error"]


def test_empty_and_fork_penalties_are_applied() -> None:
    html = """
    <html>
      <body>
        This repository is empty
        forked from upstream/project
        README
        View license
      </body>
    </html>
    """
    score, details = _run_with_html(html)
    assert score == 5
    assert details["empty_penalty"] == 20
    assert details["is_fork"] is True


def test_ci_detection_from_workflow_markers() -> None:
    html = """
    <html>
      <body>
        README
        View license
        <relative-time datetime="2999-01-01T00:00:00Z"></relative-time>
        .github/workflows
        Issues <span class="Counter">0</span>
      </body>
    </html>
    """
    score, details = _run_with_html(html)
    assert score == 100
    assert details["has_ci"] is True


def test_regular_repo_html_not_misclassified_as_not_found() -> None:
    html = """
    <html>
      <head>
        <title>example/repo</title>
      </head>
      <body>
        README
        View license
        <relative-time datetime="2999-01-01T00:00:00Z"></relative-time>
        .github/workflows
        Build artifacts reference id 4042
      </body>
    </html>
    """
    score, details = _run_with_html(html, status_code=200)
    assert score == 100
    assert details["health_score"] == 100
    assert "error" not in details


def test_get_details_unknown_repo_returns_empty_json() -> None:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}
    assert contract.get_details("https://github.com/unknown/repo") == "{}"
