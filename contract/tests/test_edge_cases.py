from __future__ import annotations

from .conftest import EMPTY_URL, RANDOM_STRING, VALID_REPO


def test_empty_string_url(fresh_contract) -> None:
    result = fresh_contract.analyze_repo(EMPTY_URL)
    assert result == 0
    assert fresh_contract.get_score(EMPTY_URL) == 0


def test_non_string_coercion(fresh_contract) -> None:
    try:
        result = fresh_contract.analyze_repo(12345)
    except Exception as error:
        assert isinstance(error, Exception)
    else:
        assert isinstance(result, int)
        assert 0 <= result <= 100
        assert fresh_contract.get_score(RANDOM_STRING) == 0


def test_very_long_url(fresh_contract) -> None:
    long_url = "https://github.com/" + ("a" * 2000)
    try:
        result = fresh_contract.analyze_repo(long_url)
    except Exception as error:
        assert isinstance(error, Exception)
    else:
        assert 0 <= result <= 100


def test_url_with_path(fresh_contract) -> None:
    url = "https://github.com/owner/repo/tree/main"
    result = fresh_contract.analyze_repo(url)
    assert 0 <= result <= 100


def test_score_idempotency_get_score(fresh_contract) -> None:
    fresh_contract.analyze_repo(VALID_REPO)
    values = [fresh_contract.get_score(VALID_REPO) for _ in range(5)]
    assert all(isinstance(v, int) for v in values)
    assert len(set(values)) == 1


def test_treemap_isolation(fresh_contract) -> None:
    repo_a = VALID_REPO
    repo_b = "https://github.com/pallets/flask"

    fresh_contract.analyze_repo(repo_a)
    score_a_before = fresh_contract.get_score(repo_a)

    fresh_contract.analyze_repo(repo_b)
    assert fresh_contract.get_score(repo_a) == score_a_before
