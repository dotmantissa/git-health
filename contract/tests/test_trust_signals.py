from __future__ import annotations

import json
from dataclasses import dataclass

import git_health


@dataclass
class _Resp:
    status_code: int
    body: bytes


def _run_analysis(html: str) -> tuple[int, dict]:
    contract = git_health.GitHealth()
    contract.repo_scores = {}
    contract.repo_details = {}

    def fake_get(_url: str):
        return _Resp(status_code=200, body=html.encode("utf-8"))

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.get = fake_get
    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    score = contract.analyze_repo("https://github.com/example/repo")
    details = json.loads(contract.get_details("https://github.com/example/repo"))
    return score, details


def test_trust_signals_all_present_no_penalty() -> None:
    html = """
    README
    View license
    .github/workflows
    <relative-time datetime="2999-01-01T00:00:00Z"></relative-time>
    Issues <span class="Counter">0</span>
    """
    score, details = _run_analysis(html)
    assert score == 100
    assert details["has_readme"] is True
    assert details["has_ci"] is True
    assert details["has_license"] is True


def test_missing_single_trust_signal_deducts_five() -> None:
    html = """
    View license
    .github/workflows
    <relative-time datetime="2999-01-01T00:00:00Z"></relative-time>
    Issues <span class="Counter">0</span>
    """
    score, _ = _run_analysis(html)
    assert score == 95


def test_missing_all_trust_signals_deducts_fifteen() -> None:
    html = """
    <relative-time datetime="2999-01-01T00:00:00Z"></relative-time>
    Issues <span class="Counter">0</span>
    """
    score, _ = _run_analysis(html)
    assert score == 85


def test_trust_signal_penalties_stack_with_issue_penalty() -> None:
    html = """
    <relative-time datetime="2999-01-01T00:00:00Z"></relative-time>
    Issues <span class="Counter">35</span>
    """
    score, details = _run_analysis(html)
    assert score == 82
    assert details["issue_penalty"] == 3
    assert details["health_score"] == 82
