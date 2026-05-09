# v0.2.0
# { "Depends": "py-genlayer:latest" }

import json
import re
from datetime import datetime, timezone
from genlayer import *


class GitHealth(gl.Contract):
    """
    Analyzes GitHub repositories to assign a Health Score (0–100).
    Uses the GitHub REST API for structured, reliable data instead of
    scraping the HTML page, which is JS-rendered and LLM-unreliable.

    Scoring breakdown (100 points total):
      - Commit recency  : up to −65 pts  (days since last COMMIT, not push)
      - Empty repo      : −20 pts        (zero commits → no history at all)
      - Open issues     : up to −20 pts  (1 pt per 10 open issues)
      - Missing README  : −5 pts
      - Missing CI      : −5 pts         (GitHub Actions, Travis, Circle, Jenkins…)
      - Missing license : −5 pts
      - Fork            : −5 pts
    """

    # repo URL → health score
    repo_scores: TreeMap[str, u256]
    # repo URL → JSON breakdown (for transparency / debugging)
    repo_details: TreeMap[str, str]

    def __init__(self):
        pass

    # ------------------------------------------------------------------ #
    #  Helpers (defined inside analyze_repo so they close over nothing)   #
    # ------------------------------------------------------------------ #

    @gl.public.write
    def analyze_repo(self, repo_url: str) -> int:
        """
        Fetches real repository data from the GitHub API, computes a health
        score, runs multi-validator consensus, and persists the result.
        """

        # --- 1. URL parser ------------------------------------------------

        def parse_github_url(url: str) -> tuple:
            """Return (owner, repo) from any github.com URL."""
            url = url.strip().rstrip("/")
            match = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", url)
            if not match:
                raise ValueError(f"Cannot parse GitHub URL: {url!r}")
            owner = match.group(1)
            repo = match.group(2)
            if repo.endswith(".git"):
                repo = repo[:-4]
            return owner, repo

        # --- 2. API fetch -------------------------------------------------

        def fetch_api(path: str):
            """
            Call the GitHub REST API and return the decoded JSON object/list.
            Returns None on any error (network, 404, parse, …).
            """
            url = f"https://api.github.com/{path}"
            try:
                raw = gl.nondet.web.render(url, mode="text")
                data = json.loads(raw)
                # GitHub returns {"message": "Not Found"} for missing resources
                if isinstance(data, dict) and "message" in data and "id" not in data:
                    print(f"API {url!r} → {data.get('message')}")
                    return None
                return data
            except Exception as exc:
                print(f"fetch_api({url!r}) failed: {exc}")
                return None

        # --- 3. Date utility ----------------------------------------------

        def days_since(iso_ts: str) -> int | None:
            """
            Parse a GitHub ISO-8601 timestamp ("2024-01-15T10:30:00Z")
            and return the number of whole days elapsed since then.
            Returns None when the timestamp is absent or unparseable.
            """
            if not iso_ts:
                return None
            try:
                dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                return max(0, (now - dt).days)
            except Exception as exc:
                print(f"days_since({iso_ts!r}) parse error: {exc}")
                return None

        # --- 4. Score computation (purely deterministic) ------------------

        def compute_score(
            repo_info: dict,
            last_commit_ts: str | None,
            has_readme: bool,
            has_ci: bool,
        ) -> tuple:
            score = 100
            breakdown: dict = {}

            # 4a. Commit recency via actual last commit date
            # last_commit_ts is None when the repo has zero commits.
            days = days_since(last_commit_ts) if last_commit_ts else None
            breakdown["last_commit_ts"] = last_commit_ts or ""
            breakdown["days_since_last_commit"] = days

            is_empty = last_commit_ts is None  # no commits at all
            breakdown["is_empty"] = is_empty

            if is_empty:
                # No commit history → maximum recency penalty + empty penalty
                recency_penalty = 65
                empty_penalty = 20
            else:
                empty_penalty = 0
                if days is None:
                    recency_penalty = 25      # Timestamp unparseable → pessimistic
                elif days <= 30:
                    recency_penalty = 0       # Active
                elif days <= 180:
                    recency_penalty = 15      # Slowing
                elif days <= 365:
                    recency_penalty = 40      # Stale
                else:
                    recency_penalty = 65      # Abandoned

            score -= recency_penalty
            score -= empty_penalty
            breakdown["recency_penalty"] = recency_penalty
            breakdown["empty_penalty"] = empty_penalty

            # 4c. Open issues
            open_issues = max(0, int(repo_info.get("open_issues_count") or 0))
            issue_penalty = min(20, open_issues // 10)
            score -= issue_penalty
            breakdown["open_issues"] = open_issues
            breakdown["issue_penalty"] = issue_penalty

            # 4d. Trust signals
            has_license = repo_info.get("license") is not None
            breakdown["has_readme"] = has_readme
            breakdown["has_ci"] = has_ci
            breakdown["has_license"] = has_license

            if not has_readme:
                score -= 5
            if not has_ci:
                score -= 5
            if not has_license:
                score -= 5

            # 4e. Fork discount (forks inherit activity they didn't generate)
            is_fork: bool = bool(repo_info.get("fork", False))
            breakdown["is_fork"] = is_fork
            if is_fork:
                score -= 5

            score = max(0, min(100, score))
            breakdown["final_score"] = score
            return score, breakdown

        # --- 5. Non-deterministic fetch + score (run by each validator) ---

        def get_repo_health() -> str:
            owner, repo = parse_github_url(repo_url)
            print(f"Analyzing {owner}/{repo} …")

            # Core metadata: open_issues_count, license, size, fork
            repo_info = fetch_api(f"repos/{owner}/{repo}")
            if not repo_info:
                return json.dumps({
                    "health_score": 0,
                    "error": "Repository not found or API unreachable",
                    "repo": repo_url,
                })

            # --- Last commit date -----------------------------------------
            # `pushed_at` on the repo object reflects branch-force-pushes and
            # non-commit events, making it unreliable for recency scoring.
            # The commits endpoint returns the actual latest commit timestamp.
            last_commit_ts = None
            commits = fetch_api(f"repos/{owner}/{repo}/commits?per_page=1")
            if isinstance(commits, list) and len(commits) > 0:
                # Shape: [{ "commit": { "committer": { "date": "…" } } }]
                try:
                    last_commit_ts = (
                        commits[0]["commit"]["committer"]["date"]
                    )
                except (KeyError, TypeError):
                    try:
                        last_commit_ts = (
                            commits[0]["commit"]["author"]["date"]
                        )
                    except (KeyError, TypeError):
                        last_commit_ts = None
            # empty list → repo has no commits at all (last_commit_ts stays None)

            # --- README presence ------------------------------------------
            readme = fetch_api(f"repos/{owner}/{repo}/readme")
            has_readme = isinstance(readme, dict) and "name" in readme

            # --- CI presence (broad: GitHub Actions + major hosted CI) ----
            # Check GitHub Actions workflows folder first (most common).
            # Then fall back to well-known root-level CI config filenames.
            # Any one hit is enough to mark CI as present.
            CI_CONFIG_FILES = [
                ".travis.yml",
                ".circleci/config.yml",
                "Jenkinsfile",
                ".drone.yml",
                "azure-pipelines.yml",
                ".gitlab-ci.yml",
                "bitbucket-pipelines.yml",
                "Makefile",          # weak signal but counts as automation
            ]

            has_ci = False

            workflows = fetch_api(
                f"repos/{owner}/{repo}/contents/.github/workflows"
            )
            if isinstance(workflows, list) and len(workflows) > 0:
                has_ci = True

            if not has_ci:
                for ci_file in CI_CONFIG_FILES:
                    result = fetch_api(
                        f"repos/{owner}/{repo}/contents/{ci_file}"
                    )
                    if isinstance(result, dict) and "name" in result:
                        has_ci = True
                        break

            score, breakdown = compute_score(
                repo_info, last_commit_ts, has_readme, has_ci
            )

            breakdown["health_score"] = score
            breakdown["owner"] = owner
            breakdown["repo"] = repo

            print(f"Score for {owner}/{repo}: {score}")
            print(f"Breakdown: {json.dumps(breakdown)}")
            return json.dumps(breakdown)

        # --- 6. Multi-validator consensus ---------------------------------

        consensus_instruction = """
        Compare the 'health_score' integer values across all validator results.
        Accept the result if all scores differ by at most 5 points
        (e.g. 74 and 79 → accept; 74 and 80 → reject).
        When scores differ within tolerance, prefer the result with the
        lower (more conservative) health_score.
        """

        final_json_str = gl.eq_principle.prompt_comparative(
            get_repo_health,
            consensus_instruction,
        )

        # --- 7. Persist ---------------------------------------------------

        parsed = json.loads(final_json_str)
        score = int(parsed["health_score"])

        self.repo_scores[repo_url] = u256(score)
        self.repo_details[repo_url] = final_json_str
        return score

    # ------------------------------------------------------------------ #
    #  Read-only views                                                     #
    # ------------------------------------------------------------------ #

    @gl.public.view
    def get_score(self, repo_url: str) -> int:
        """Return the cached health score, or 0 if not yet analyzed."""
        if repo_url in self.repo_scores:
            return int(self.repo_scores[repo_url])
        return 0

    @gl.public.view
    def get_details(self, repo_url: str) -> str:
        """Return the full JSON breakdown from the last analysis."""
        if repo_url in self.repo_details:
            return self.repo_details[repo_url]
        return "{}"
