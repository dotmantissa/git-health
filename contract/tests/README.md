# GitHealth Contract Tests

## Prerequisites

- Python 3.11+
- GenLayer SDK installed
- GenLayer Studio running (for environments that require it)

## Install

```bash
pip install -e ".[dev]"
```

## Run Tests

```bash
pytest
```

## Run Linter

```bash
ruff check . && ruff format --check .
```

## Note on Non-Determinism

`analyze_repo` uses LLM consensus, so scores may vary across runs. Tests focus on
bounds, types, and state consistency rather than exact score values.
