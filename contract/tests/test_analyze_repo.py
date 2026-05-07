from __future__ import annotations

from .conftest import INVALID_URL, VALID_REPO


def _assert_score_bounds(value: int) -> None:
    assert isinstance(value, int)
    assert 0 <= value <= 100


def test_analyze_valid_repo(fresh_contract) -> None:
    score = fresh_contract.analyze_repo(VALID_REPO)
    _assert_score_bounds(score)

    stored = fresh_contract.get_score(VALID_REPO)
    assert stored == score
    assert stored >= 0


def test_analyze_stores_score(fresh_contract) -> None:
    first = fresh_contract.analyze_repo(VALID_REPO)
    _assert_score_bounds(first)

    second = fresh_contract.analyze_repo(VALID_REPO)
    _assert_score_bounds(second)

    latest = fresh_contract.get_score(VALID_REPO)
    assert latest == second


def test_analyze_multiple_repos(fresh_contract) -> None:
    repo_a = VALID_REPO
    repo_b = "https://github.com/pallets/flask"

    score_a = fresh_contract.analyze_repo(repo_a)
    score_b = fresh_contract.analyze_repo(repo_b)

    _assert_score_bounds(score_a)
    _assert_score_bounds(score_b)
    assert fresh_contract.get_score(repo_a) == score_a
    assert fresh_contract.get_score(repo_b) == score_b


def test_analyze_invalid_url_returns_zero(fresh_contract) -> None:
    result = fresh_contract.analyze_repo(INVALID_URL)
    assert result == 0
    assert fresh_contract.get_score(INVALID_URL) == 0


def test_analyze_returns_int(fresh_contract) -> None:
    result = fresh_contract.analyze_repo(VALID_REPO)
    assert isinstance(result, int)
    assert result >= 0
