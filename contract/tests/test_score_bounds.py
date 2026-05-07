from __future__ import annotations

import logging

import pytest

from .conftest import INACTIVE_REPO, VALID_REPO

logger = logging.getLogger(__name__)

REPOS = [
    "https://github.com/ethereum/go-ethereum",
    "https://github.com/pallets/flask",
    "https://github.com/psf/requests",
    "https://github.com/python/cpython",
]


@pytest.mark.parametrize("repo_url", REPOS)
def test_score_never_exceeds_100(fresh_contract, repo_url: str) -> None:
    score = fresh_contract.analyze_repo(repo_url)
    assert score <= 100


@pytest.mark.parametrize("repo_url", REPOS)
def test_score_never_negative(fresh_contract, repo_url: str) -> None:
    score = fresh_contract.analyze_repo(repo_url)
    assert score >= 0


@pytest.mark.parametrize("repo_url", REPOS)
def test_score_is_integer(fresh_contract, repo_url: str) -> None:
    score = fresh_contract.analyze_repo(repo_url)
    assert isinstance(score, int)


@pytest.mark.parametrize(
    "repo_url",
    [
        VALID_REPO,
        "https://github.com/pallets/flask",
    ],
)
def test_score_consistent_with_stored_value(fresh_contract, repo_url: str) -> None:
    result = fresh_contract.analyze_repo(repo_url)
    stored = fresh_contract.get_score(repo_url)
    assert result == stored


@pytest.mark.xfail(strict=False, reason="LLM consensus may vary across runs")
def test_inactive_repo_scores_lower_on_average(fresh_contract) -> None:
    active_score = fresh_contract.analyze_repo(VALID_REPO)
    inactive_score = fresh_contract.analyze_repo(INACTIVE_REPO)

    logger.info("Active repo score: %s", active_score)
    logger.info("Inactive repo score: %s", inactive_score)

    assert 0 <= active_score <= 100
    assert 0 <= inactive_score <= 100
    assert inactive_score <= active_score
