# git-health

On-chain GitHub repository health scoring via GenLayer intelligent contracts and validator consensus.

## Current Architecture

- `contract/git_health.py`: GenLayer intelligent contract that computes and stores health scores.
- `src/`: React + Vite frontend for wallet connection, analyze transactions, cached reads, and score history.
- `contract/tests/`: Contract unit tests covering scoring, trust signals, bounds, and v0.2.0 API behavior.

## Deployed Frontend

- Production URL: `https://git-health.vercel.app`

## How The dApp Works

1. User connects wallet (MetaMask-compatible) on GenLayer Studio network (`chainId = 61999`).
2. User submits a GitHub repo URL to `analyze_repo(repo_url)`.
3. Contract fetches repository signals from GitHub:
- Primary source: GitHub REST API (`api.github.com`)
- Fallback/augmentation source: GitHub repo HTML page parsing
4. Each validator returns a JSON breakdown including `health_score`.
5. Consensus accepts results only when all validator `health_score` values are within 5 points.
6. If accepted, the most conservative value (lowest score) is selected.
7. Contract stores both:
- `repo_scores[repo_url]` (numeric score)
- `repo_details[repo_url]` (full JSON breakdown)
8. Frontend reads results via `get_score` and `get_details`.

## Contract Logic (v0.2.0)

### Data collection behavior

- Parses `owner/repo` from GitHub URL.
- Uses GitHub API first (`/repos/{owner}/{repo}`, commits, readme, contents, workflows).
- Uses HTML parsing as fallback and to fill missing signals.
- If API and HTML both fail, returns previous cached score with error metadata:
  - `"used_cached_score": true`

### Scoring model

Score starts at `100`, then deductions are applied:

- Commit recency:
- Unknown date: `-25`
- `<= 30 days`: `-0`
- `31-180 days`: `-15`
- `181-365 days`: `-40`
- `> 365 days`: `-65`
- Empty repo: `-20` and recency penalty treated as `-65`
- Open issues: `min(20, open_issues_count // 10)`
- Missing trust signals:
- No README: `-5`
- No CI/workflows: `-5`
- No license: `-5`
- Forked repo: `-5`

Guardrails:
- Final score is clamped to `[0, 100]`.
- `get_score(repo_url)` returns cached score or `0` if never analyzed.
- `get_details(repo_url)` returns the last JSON breakdown or `{}` if none exists.

## Frontend Behavior

- Network-gated to GenLayer Studio (`chainId 61999`, hex `0xF22F`).
- Contract calls use `genlayer-js` with `studionet`.
- Analyze flow:
- Submits `analyze_repo` transaction.
- Waits for `FINALIZED` receipt.
- Verifies execution success from leader/validator execution status.
- On success, reads and displays `get_score` + `get_details`.
- On execution failure, attempts `debugTraceTransaction` for diagnostics.
- Cached read flow:
- Calls `get_score` + `get_details` without submitting a tx.
- UI keeps per-session history of analyzed/read entries.

## Configuration

`.env.example`:

```env
VITE_CONTRACT_ADDRESS=0xe573CcD25aF2bC2177817261E3207D9F4bf7b667
VITE_CHAIN_ID=61999
VITE_RPC_URL=http://localhost:4000/api
```

Address resolution behavior:
- Uses `VITE_CONTRACT_ADDRESS` when set and non-zero.
- Falls back to `src/constants.js` default address when missing/zero.

## Local Development

Prerequisites:
- Python `3.11+`
- Node.js `20+`
- GenLayer Studio running locally (`http://localhost:4000`)
- MetaMask or compatible EIP-1193 wallet

Install and run frontend:

```bash
cp .env.example .env
npm install
npm run dev
```

## Contract Tests

Run all contract tests:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q contract/tests -v
```

## Linting

```bash
ruff check contract/git_health.py contract/tests/
ruff format --check contract/git_health.py contract/tests/
```
