from __future__ import annotations

from .conftest import EMPTY_URL, VALID_REPO


def test_get_score_unanalyzed_returns_zero(fresh_contract) -> None:
    assert fresh_contract.get_score(VALID_REPO) == 0


def test_get_score_after_analyze(fresh_contract) -> None:
    analyzed = fresh_contract.analyze_repo(VALID_REPO)
    stored = fresh_contract.get_score(VALID_REPO)
    assert stored == analyzed


def test_get_score_empty_url_returns_zero(fresh_contract) -> None:
    assert fresh_contract.get_score(EMPTY_URL) == 0


def test_get_score_unknown_url_returns_zero(fresh_contract) -> None:
    url = "https://github.com/nobody/doesnotexist12345678"
    assert fresh_contract.get_score(url) == 0


def test_get_score_is_view_only(fresh_contract) -> None:
    first = fresh_contract.get_score(VALID_REPO)
    second = fresh_contract.get_score(VALID_REPO)
    assert first == second
