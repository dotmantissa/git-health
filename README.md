# git-health

> On-chain GitHub repository health scoring via GenLayer intelligent contracts and LLM consensus.

## Repository structure

| Directory | Purpose |
|-----------|---------|
| `contract/` | GenLayer intelligent contract (`git_health.py`) + pytest test suite |
| `frontend/` | React + Vite dApp — connects to GenLayer Studio, calls the contract |
| `.github/workflows/` | CI: lint, test, and build on every push |

## Prerequisites

- Python 3.11+
- Node.js 20+
- GenLayer Studio running locally on `http://localhost:4000`
- MetaMask (or compatible EIP-1193 wallet)

## Quickstart

### 1. Deploy the contract

Use GenLayer Studio CLI or Studio UI to deploy `contract/git_health.py`, then copy the deployed contract address.

### 2. Run the frontend

```bash
cd frontend
cp .env.example .env
# Set VITE_CONTRACT_ADDRESS in .env to your deployed contract address
npm install
npm run dev
```

### 3. Run the tests

```bash
cd contract
pip install pytest pytest-asyncio genlayer ruff
pytest tests/ -v
```

### 4. Lint

```bash
ruff check git_health.py tests/
ruff format --check git_health.py tests/
```

## Network

This app is strictly locked to GenLayer Studio (Chain ID 61999). It will not function on any other network.
