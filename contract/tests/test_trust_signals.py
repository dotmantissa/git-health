from __future__ import annotations

import json

import git_health


def _run_analysis(extracted_payload: dict) -> int:
    contract = git_health.GitHealth()
    contract.repo_scores = {}

    def fake_render(_repo_url: str, mode: str = "text") -> str:
        assert mode == "text"
        return "mock github page content"

    def fake_exec_prompt(_task: str, response_format: str | None = None) -> str:
        _ = response_format
        return json.dumps(extracted_payload)

    def fake_comparative(callback, _instruction: str) -> str:
        return callback()

    git_health.gl.nondet.web.render = fake_render
    git_health.gl.nondet.exec_prompt = fake_exec_prompt
    git_health.gl.eq_principle.prompt_comparative = fake_comparative

    return contract.analyze_repo("https://github.com/example/repo")


def test_trust_signals_all_present_no_penalty() -> None:
    payload = {
        "last_commit_text": "committed 2 days ago",
        "commit_recency_bucket": "within_1_month",
        "open_issues_count": 0,
        "has_readme": True,
        "has_ci": True,
        "has_license": True,
        "confidence": "high",
    }
    assert _run_analysis(payload) == 100


def test_missing_single_trust_signal_deducts_five() -> None:
    payload = {
        "last_commit_text": "committed 2 days ago",
        "commit_recency_bucket": "within_1_month",
        "open_issues_count": 0,
        "has_readme": False,
        "has_ci": True,
        "has_license": True,
        "confidence": "high",
    }
    assert _run_analysis(payload) == 95


def test_missing_all_trust_signals_deducts_fifteen() -> None:
    payload = {
        "last_commit_text": "committed 2 days ago",
        "commit_recency_bucket": "within_1_month",
        "open_issues_count": 0,
        "has_readme": False,
        "has_ci": False,
        "has_license": False,
        "confidence": "high",
    }
    assert _run_analysis(payload) == 85


def test_trust_signal_penalties_stack_with_issue_penalty() -> None:
    payload = {
        "last_commit_text": "committed 2 days ago",
        "commit_recency_bucket": "within_1_month",
        "open_issues_count": 35,  # issue penalty = 3
        "has_readme": False,
        "has_ci": False,
        "has_license": False,
        "confidence": "high",
    }
    assert _run_analysis(payload) == 82
