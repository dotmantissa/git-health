# git-health

> On-chain GitHub repository health scoring via GenLayer intelligent contracts and validator consensus.

## What changed recently

- Contract now uses the GitHub REST API (`api.github.com`) instead of HTML scraping.
- Added persisted JSON score breakdowns via `get_details(repo_url)`.
- Frontend default contract address updated to:
  - `0xA10Fe4e8d3F3e8b81cB11F8B97CA5d7Cc57381c1`
- Production frontend is deployed on Vercel at:
  - `https://git-health.vercel.app`

## Repository structure (current)

| Directory | Purpose |
|-----------|---------|
| `contract/` | GenLayer intelligent contract (`git_health.py`) + pytest tests |
| `src/` | React + Vite dApp — wallet UX + contract calls |
| `.github/workflows/` | CI: lint, test, and build on every push |
| `.env.example` | Frontend environment template (`VITE_CONTRACT_ADDRESS`, chain, RPC) |

## Prerequisites

- Python 3.11+ (recommended for full GenLayer SDK compatibility)
- Node.js 20+
- GenLayer Studio running locally on `http://localhost:4000`
- MetaMask (or compatible EIP-1193 wallet)

## Quickstart

### 1. Deploy the contract

Use GenLayer Studio CLI or Studio UI to deploy `contract/git_health.py`, then copy the deployed contract address.

### 2. Run the frontend

```bash
cp .env.example .env
# Set VITE_CONTRACT_ADDRESS in .env to your deployed contract address
npm install
npm run dev
```

### 3. Run the tests

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q contract/tests/test_trust_signals.py contract/tests/test_v020_api_behavior.py -v
```

### 4. Lint

```bash
ruff check contract/git_health.py contract/tests/
ruff format --check contract/git_health.py contract/tests/
```

## Contract scoring model (`contract/git_health.py`)

Score starts at `100`, then deductions are applied:

- Commit recency:
  - unknown: `-25`
  - `<= 30` days: `-0`
  - `31–180` days: `-15`
  - `181–365` days: `-40`
  - `> 365` days: `-65`
- Empty repository (`size == 0`): `-20`
- Open issues: `min(20, open_issues_count // 10)`
- Trust signals:
  - missing README: `-5`
  - missing CI/workflow: `-5`
  - missing license: `-5`
- Fork repository: `-5`

Guardrails:
- Score is clamped to `[0, 100]`
- Consensus accepts validator results only when all `health_score` values are within 5 points, choosing the lower score when in-range.

## Environment variable behavior

- Frontend uses `VITE_CONTRACT_ADDRESS` when set.
- If that env var is empty or `0x0000000000000000000000000000000000000000`, it falls back to the default in `src/constants.js`.

## Network

This app is strictly locked to GenLayer Studio (Chain ID 61999). It will not function on any other network.
