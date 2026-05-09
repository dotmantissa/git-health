from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

VALID_REPO = "https://github.com/ethereum/go-ethereum"
INACTIVE_REPO = "https://github.com/torvalds/linux"
INVALID_URL = "https://notgithub.com/user/repo"
EMPTY_URL = ""
RANDOM_STRING = "not_a_url_at_all"

CONTRACT_PATH = Path(__file__).resolve().parent.parent / "git_health.py"

try:
    from genlayer.testing import ContractRunner  # type: ignore[attr-defined]
except ImportError:
    try:
        from genlayer.test import ContractRunner  # type: ignore[attr-defined]
    except ImportError as err:
        ContractRunner = None  # type: ignore[assignment]
        _IMPORT_ERROR = err
    else:
        _IMPORT_ERROR = None
else:
    _IMPORT_ERROR = None


class _ContractAdapter:
    """Adapts minor SDK API differences (invoke/call vs method access)."""

    def __init__(self, instance: Any):
        self._instance = instance

    def analyze_repo(self, repo_url: Any) -> Any:
        if hasattr(self._instance, "analyze_repo"):
            return self._instance.analyze_repo(repo_url)
        if hasattr(self._instance, "invoke"):
            return self._instance.invoke("analyze_repo", repo_url)
        raise AttributeError("Contract instance has no analyze_repo or invoke")

    def get_score(self, repo_url: Any) -> Any:
        if hasattr(self._instance, "get_score"):
            return self._instance.get_score(repo_url)
        if hasattr(self._instance, "call"):
            return self._instance.call("get_score", repo_url)
        raise AttributeError("Contract instance has no get_score or call")

    def get_details(self, repo_url: Any) -> Any:
        if hasattr(self._instance, "get_details"):
            return self._instance.get_details(repo_url)
        if hasattr(self._instance, "call"):
            return self._instance.call("get_details", repo_url)
        raise AttributeError("Contract instance has no get_details or call")


@pytest.fixture(scope="session")
def runner() -> Any:
    if ContractRunner is None:
        pytest.skip(f"genlayer ContractRunner unavailable: {_IMPORT_ERROR}")

    try:
        return ContractRunner(str(CONTRACT_PATH))
    except TypeError:
        return ContractRunner(contract_path=str(CONTRACT_PATH))


@pytest.fixture(scope="function")
def fresh_contract(runner: Any) -> _ContractAdapter:
    if hasattr(runner, "deploy"):
        deployed = runner.deploy()
    elif hasattr(runner, "new"):
        deployed = runner.new()
    else:
        raise AttributeError("ContractRunner has no deploy/new method")

    return _ContractAdapter(deployed)
