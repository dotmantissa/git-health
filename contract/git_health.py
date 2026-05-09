# v0.2.0
# { "Depends": "py-genlayer:latest" }

import json
import re
from datetime import datetime, timezone
from genlayer import *


class GitHealth(gl.Contract):
    """
    Analyzes GitHub repositories and assigns a Health Score (0-100).

    Scoring:
      Commit recency  up to -65 pts  (days since last actual commit)
      Empty repo           -20 pts   (zero commits)
      Open issues     up to -20 pts  (1 pt per 10 open issues, max 20)
      No README             -5 pts
      No CI                 -5 pts   (Actions, Travis, Circle, Drone, etc.)
      No license            -5 pts
      Fork                  -5 pts
    """

    repo_scores: TreeMap[str, u256]
    repo_details: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def analyze_repo(self, repo_url: str) -> int:

        # ── helpers (deterministic, defined outside the nondet block) ──────

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
                recency_penalty, empty_penalty = 65, 20
                bk["days_since_last_commit"] = None
            else:
                empty_penalty = 0
                days = days_since(last_commit_ts)
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

            for key, penalty in [
                ("has_readme", 5),
                ("has_ci", 5),
                ("has_license", 5),
            ]:
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

        # ── parse owner/repo BEFORE the nondet block ────────────────────────
        # self is accessible here; it is NOT accessible inside get_repo_health
        owner, repo = parse_github_url(repo_url)

        # ── nondet block: each validator runs this independently ────────────
        def get_repo_health() -> str:
            """
            Uses gl.nondet.web.get() — the correct raw HTTP client.
            gl.nondet.web.render() is a JS page renderer and must NOT be
            used for JSON API endpoints; it returns mangled HTML, not bytes.
            """

            CI_FILES = {
                ".travis.yml", ".drone.yml", "azure-pipelines.yml",
                ".gitlab-ci.yml", "bitbucket-pipelines.yml",
                "Jenkinsfile", "Makefile",
            }
            CI_DIRS = {".circleci", ".github"}

            def fetch(path: str):
                """
                Raw HTTP GET against the GitHub REST API.
                Returns parsed JSON (dict or list), [] for empty repos,
                or None on error / not-found.
                """
                url = f"https://api.github.com/{path}"
                try:
                    resp = gl.nondet.web.get(url)
                except Exception as exc:
                    print(f"fetch({path!r}): network error: {exc}")
                    return None

                body = resp.body.decode("utf-8")

                # 409 Conflict = "Git Repository is empty."
                if resp.status_code == 409:
                    return []

                if resp.status_code >= 400:
                    print(f"fetch({path!r}): HTTP {resp.status_code} — {body[:120]}")
                    return None

                try:
                    data = json.loads(body)
                except json.JSONDecodeError as exc:
                    print(f"fetch({path!r}): JSON parse error: {exc} — {body[:120]}")
                    return None

                # GitHub error envelope: {"message": "Not Found", ...}
                if isinstance(data, dict) and "message" in data and "id" not in data:
                    msg = data["message"]
                    print(f"fetch({path!r}): GitHub error: {msg!r}")
                    if "empty" in msg.lower():
                        return []
                    return None

                return data

            # 1. Core repo metadata
            repo_info = fetch(f"repos/{owner}/{repo}")
            if not isinstance(repo_info, dict):
                return json.dumps({
                    "health_score": 0,
                    "error": "repo metadata fetch failed",
                    "owner": owner,
                    "repo": repo,
                })

            # 2. Last commit timestamp
            # NOTE: pushed_at on the repo object updates on any branch event,
            # not just commits. We fetch /commits?per_page=1 for accuracy.
            is_empty = False
            last_commit_ts = None
            commits = fetch(f"repos/{owner}/{repo}/commits?per_page=1")
            if commits == []:
                is_empty = True
            elif isinstance(commits, list) and len(commits) > 0:
                try:
                    last_commit_ts = commits[0]["commit"]["committer"]["date"]
                except (KeyError, TypeError):
                    try:
                        last_commit_ts = commits[0]["commit"]["author"]["date"]
                    except (KeyError, TypeError):
                        pass

            # 3. README
            readme = fetch(f"repos/{owner}/{repo}/readme")
            has_readme = isinstance(readme, dict) and "name" in readme

            # 4. CI detection — one root listing call, one workflows call
            #    (avoids the old 9-call per-filename loop)
            has_ci = False
            root = fetch(f"repos/{owner}/{repo}/contents/")
            if isinstance(root, list):
                names = {str(item.get("name", "")) for item in root}
                has_ci = bool((names & CI_FILES) or (names & CI_DIRS))
            if not has_ci:
                wf = fetch(f"repos/{owner}/{repo}/contents/.github/workflows")
                has_ci = isinstance(wf, list) and len(wf) > 0

            data = {
                "is_empty":          is_empty,
                "last_commit_ts":    last_commit_ts,
                "open_issues_count": repo_info.get("open_issues_count", 0),
                "has_license":       repo_info.get("license") is not None,
                "is_fork":           bool(repo_info.get("fork", False)),
                "has_readme":        has_readme,
                "has_ci":            has_ci,
            }

            score, breakdown = compute_score(data)
            breakdown["owner"] = owner
            breakdown["repo"] = repo
            print(f"Score {owner}/{repo}: {score} | {json.dumps(breakdown)}")
            return json.dumps(breakdown)

        # ── consensus: all validators must agree within 5 points ───────────
        final_json_str = gl.eq_principle.prompt_comparative(
            get_repo_health,
            """
            Compare the 'health_score' integer in each validator result.
            Accept when all scores differ by at most 5 points.
            When within tolerance, select the result with the lowest score
            (most conservative estimate).
            """,
        )

        # ── persist ────────────────────────────────────────────────────────
        parsed = json.loads(final_json_str)
        score = int(parsed["health_score"])
        self.repo_scores[repo_url] = u256(score)
        self.repo_details[repo_url] = final_json_str
        return score

    @gl.public.view
    def get_score(self, repo_url: str) -> int:
        """Return the last cached health score, or 0 if never analyzed."""
        if repo_url in self.repo_scores:
            return int(self.repo_scores[repo_url])
        return 0

    @gl.public.view
    def get_details(self, repo_url: str) -> str:
        """Return the full JSON breakdown from the last analysis."""
        if repo_url in self.repo_details:
            return self.repo_details[repo_url]
        return "{}"
