# git-health

> On-chain GitHub repository health scoring via GenLayer intelligent contracts and LLM consensus.

## What changed recently

- Contract scoring now includes trust signals from the GitHub repo page:
  - `README` presence
  - CI/workflow presence
  - License presence
- Contract LLM calls now request JSON output explicitly (`response_format="json"`) and handle both dict and JSON-string responses.
- Added deterministic tests for trust-signal scoring in `contract/tests/test_trust_signals.py`.
- Frontend default contract address updated to:
  - `0xD9d8E22211b4943cd7ea05F68af8B28c72966eAF`
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
pytest -q contract/tests/test_trust_signals.py -v
```

### 4. Lint

```bash
ruff check contract/git_health.py contract/tests/
ruff format --check contract/git_health.py contract/tests/
```

## Contract scoring model (`contract/git_health.py`)

Score starts at `100`, then deductions are applied:

- Commit recency:
  - missing/unknown: `-10`
  - over 1 month: `-10`
  - over 6 months: `-40`
  - over 1 year: `-60`
- Open issues: `min(20, open_issues_count // 10)`
- Trust signals:
  - missing README: `-5`
  - missing CI/workflow: `-5`
  - missing license: `-5`

Guardrails:
- Score is clamped to `[0, 100]`
- Low-confidence extraction caps optimistic high scores
- A second LLM pass is used when commit recency extraction is weak/unknown

## Environment variable behavior

- Frontend uses `VITE_CONTRACT_ADDRESS` when set.
- If that env var is empty or `0x0000000000000000000000000000000000000000`, it falls back to the default in `src/constants.js`.

## Network

This app is strictly locked to GenLayer Studio (Chain ID 61999). It will not function on any other network.
