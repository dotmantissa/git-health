# v0.2.0
# { "Depends": "py-genlayer:latest" }

import json
import re
from datetime import datetime, timezone
from genlayer import *


class GitHealth(gl.Contract):
    """
    Analyzes GitHub repositories and assigns a Health Score (0-100).

    Data source: raw HTML of github.com/owner/repo (no API, no auth needed).
    gl.nondet.web.get() is used exactly as shown in the official GenLayer
    "Fetch GitHub Profile" example. The GitHub REST API was silently returning
    403 (missing User-Agent) causing every score to be 0.

    Scoring:
      Commit recency  up to -65 pts  (extracted from datetime= HTML attribute)
      Empty repo           -20 pts   (zero commits)
      Open issues     up to -20 pts  (1 pt per 10, max 20)
      No README             -5 pts
      No CI                 -5 pts
      No license            -5 pts
      Fork                  -5 pts
    """

    repo_scores: TreeMap[str, u256]
    repo_details: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def analyze_repo(self, repo_url: str) -> int:

        # ── deterministic helpers ───────────────────────────────────────────

        def parse_github_url(url: str) -> tuple:
            url = url.strip().rstrip("/")
            m = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", url)
            if not m:
                raise ValueError(f"Cannot parse GitHub URL: {url!r}")
            owner = m.group(1)
            repo = m.group(2)
            if repo.endswith(".git"):
                repo = repo[:-4]
            return owner, repo

        def days_since(iso_ts: str):
            if not iso_ts:
                return None
            try:
                dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
                return max(0, (datetime.now(timezone.utc) - dt).days)
            except Exception:
                return None

        def compute_score(d: dict) -> tuple:
            score = 100
            bk = {}

            is_empty = bool(d.get("is_empty", False))
            last_commit_ts = d.get("last_commit_ts") or ""
            bk["is_empty"] = is_empty
            bk["last_commit_ts"] = last_commit_ts

            if is_empty:
                recency_penalty = 65
                empty_penalty = 20
                bk["days_since_last_commit"] = None
            else:
                empty_penalty = 0
                days = days_since(last_commit_ts) if last_commit_ts else None
                bk["days_since_last_commit"] = days
                if days is None:
                    recency_penalty = 25
                elif days <= 30:
                    recency_penalty = 0
                elif days <= 180:
                    recency_penalty = 15
                elif days <= 365:
                    recency_penalty = 40
                else:
                    recency_penalty = 65

            score -= recency_penalty + empty_penalty
            bk["recency_penalty"] = recency_penalty
            bk["empty_penalty"] = empty_penalty

            open_issues = max(0, int(d.get("open_issues_count") or 0))
            issue_penalty = min(20, open_issues // 10)
            score -= issue_penalty
            bk["open_issues"] = open_issues
            bk["issue_penalty"] = issue_penalty

            for key, penalty in [("has_readme", 5), ("has_ci", 5), ("has_license", 5)]:
                val = bool(d.get(key, False))
                bk[key] = val
                if not val:
                    score -= penalty

            is_fork = bool(d.get("is_fork", False))
            bk["is_fork"] = is_fork
            if is_fork:
                score -= 5

            score = max(0, min(100, score))
            bk["health_score"] = score
            return score, bk

        # ── parse BEFORE the nondet block (self not accessible inside) ──────
        owner, repo = parse_github_url(repo_url)
        page_url = f"https://github.com/{owner}/{repo}"

        # ── nondet block ────────────────────────────────────────────────────
        def get_repo_health() -> str:
            """
            Fetch the repository HTML page using gl.nondet.web.get() —
            the exact pattern from the official GenLayer "Fetch GitHub Profile"
            example. No GitHub API, no authentication, no User-Agent issue.

            All signals are extracted from server-rendered HTML with regex,
            so there is no LLM involved and scoring is fully deterministic.
            """
            try:
                resp = gl.nondet.web.get(page_url)
            except Exception as exc:
                return json.dumps({"health_score": 0,
                                   "error": f"network error: {exc}",
                                   "owner": owner, "repo": repo})

            if resp.status_code == 404:
                return json.dumps({"health_score": 0,
                                   "error": "repository not found (404)",
                                   "owner": owner, "repo": repo})
            if resp.status_code >= 400:
                return json.dumps({"health_score": 0,
                                   "error": f"HTTP {resp.status_code}",
                                   "owner": owner, "repo": repo})

            html = resp.body.decode("utf-8", errors="replace")

            # ── Empty repo ──────────────────────────────────────────────────
            # GitHub shows a specific empty-state banner when no commits exist
            is_empty = bool(re.search(
                r"(This repository is empty|blankslate|no commits yet)",
                html, re.IGNORECASE
            ))

            # ── Last commit timestamp ───────────────────────────────────────
            # GitHub server-renders ISO timestamps in datetime= attributes on
            # <relative-time> / <time-ago> / <time> elements. The FIRST one
            # on the repo landing page is always the most recent commit date
            # (shown in the commit summary row above the file table).
            last_commit_ts = None
            if not is_empty:
                ts_match = re.search(
                    r'datetime="(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"',
                    html
                )
                if ts_match:
                    last_commit_ts = ts_match.group(1)

            # ── Fork ────────────────────────────────────────────────────────
            is_fork = bool(re.search(r"forked from", html, re.IGNORECASE))

            # ── README ──────────────────────────────────────────────────────
            # GitHub renders a README section heading and the file in the table
            has_readme = bool(re.search(r"README", html))

            # ── License ─────────────────────────────────────────────────────
            # GitHub shows "View license" or a license sidebar widget
            has_license = bool(re.search(
                r"(View license|MIT License|Apache License|BSD License"
                r"|GPL|LGPL|ISC License|Unlicense|license)",
                html, re.IGNORECASE
            ))

            # ── Open issues ─────────────────────────────────────────────────
            # GitHub puts the issue count in a <span class="Counter"> near
            # the Issues tab. Pattern is stable across GitHub HTML versions.
            open_issues = 0
            issues_match = re.search(
                r'Issues[^<]{0,200}?<span[^>]*class="[^"]*Counter[^"]*"[^>]*>'
                r'\s*([\d,]+)\s*</span>',
                html, re.DOTALL | re.IGNORECASE
            )
            if issues_match:
                try:
                    open_issues = int(issues_match.group(1).replace(",", ""))
                except ValueError:
                    open_issues = 0

            # ── CI ──────────────────────────────────────────────────────────
            # Check for links/references to .github/workflows in the file tree,
            # or well-known CI badge URLs that GitHub renders in the README.
            has_ci = bool(re.search(
                r"(\.github/workflows"
                r"|travis-ci\.com|travis-ci\.org"
                r"|circleci\.com"
                r"|github\.com/[^/]+/[^/]+/actions"
                r"|drone\.io"
                r"|azure-pipelines)",
                html, re.IGNORECASE
            ))

            data = {
                "is_empty": is_empty,
                "last_commit_ts": last_commit_ts,
                "open_issues_count": open_issues,
                "has_license": has_license,
                "is_fork": is_fork,
                "has_readme": has_readme,
                "has_ci": has_ci,
            }

            score, breakdown = compute_score(data)
            breakdown["owner"] = owner
            breakdown["repo"] = repo
            print(f"Score {owner}/{repo}: {score} | {json.dumps(breakdown)}")
            return json.dumps(breakdown)

        # ── multi-validator consensus ────────────────────────────────────────
        final_json_str = gl.eq_principle.prompt_comparative(
            get_repo_health,
            """
            Compare the 'health_score' integer across all validator results.
            Accept the result if all scores differ by at most 5 points.
            When within tolerance, prefer the result with the lowest score
            (most conservative estimate wins).
            """,
        )

        # ── persist ─────────────────────────────────────────────────────────
        parsed = json.loads(final_json_str)
        score = int(parsed["health_score"])
        self.repo_scores[repo_url] = u256(score)
        self.repo_details[repo_url] = final_json_str
        return score

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
