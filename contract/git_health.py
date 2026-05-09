# v0.2.0
# { "Depends": "py-genlayer:latest" }

import json
import re
from datetime import datetime, timezone
from genlayer import *


class GitHealth(gl.Contract):
    """
    Analyzes GitHub repositories and assigns a Health Score (0-100).

    Data source: GitHub REST API first, with HTML fallback when API calls fail.
    This avoids all-zero outcomes when one source is rate-limited or blocked.

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
        api_base = "https://api.github.com"
        previous_score = int(self.repo_scores[repo_url]) if repo_url in self.repo_scores else 0

        # ── nondet block ────────────────────────────────────────────────────
        def get_repo_health() -> str:
            """
            Primary path: GitHub REST API via gl.nondet.web.get().
            Fallback path: parse server-rendered GitHub HTML when API fails.
            This keeps scoring deterministic and resilient to partial outages.
            """
            def http_get(url: str):
                try:
                    return gl.nondet.web.get(url)
                except Exception as exc:
                    print(f"GET failed for {url!r}: {exc}")
                    return None

            def decode_body(resp) -> str:
                if resp is None:
                    return ""
                try:
                    return resp.body.decode("utf-8", errors="replace")
                except Exception:
                    return ""

            def fetch_api(path: str):
                resp = http_get(f"{api_base}/{path}")
                if resp is None:
                    return None, None
                code = int(resp.status_code)
                body = decode_body(resp)
                if code == 409:
                    return [], code
                if code >= 400:
                    return None, code
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    return None, code
                if isinstance(data, dict) and "message" in data and "id" not in data:
                    msg = str(data.get("message", ""))
                    if "empty" in msg.lower():
                        return [], code
                    return None, code
                return data, code

            def parse_html_signals(html: str):
                if not html:
                    return None
                is_empty_html = bool(re.search(
                    r"(This repository is empty|blankslate|no commits yet)",
                    html, re.IGNORECASE
                ))
                last_commit_html = None
                if not is_empty_html:
                    ts_match = re.search(
                        r'datetime="(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"',
                        html
                    )
                    if ts_match:
                        last_commit_html = ts_match.group(1)
                issues = 0
                issues_match = re.search(
                    r'Issues[^<]{0,200}?<span[^>]*class="[^"]*Counter[^"]*"[^>]*>'
                    r'\s*([\d,]+)\s*</span>',
                    html, re.DOTALL | re.IGNORECASE
                )
                if issues_match:
                    try:
                        issues = int(issues_match.group(1).replace(",", ""))
                    except ValueError:
                        issues = 0
                return {
                    "is_empty": is_empty_html,
                    "last_commit_ts": last_commit_html,
                    "open_issues_count": issues,
                    "has_license": bool(re.search(
                        r"(View license|MIT License|Apache License|BSD License"
                        r"|GPL|LGPL|ISC License|Unlicense|license)",
                        html, re.IGNORECASE
                    )),
                    "is_fork": bool(re.search(r"forked from", html, re.IGNORECASE)),
                    "has_readme": bool(re.search(r"README", html)),
                    "has_ci": bool(re.search(
                        r"(\.github/workflows"
                        r"|travis-ci\.com|travis-ci\.org"
                        r"|circleci\.com"
                        r"|github\.com/[^/]+/[^/]+/actions"
                        r"|drone\.io"
                        r"|azure-pipelines)",
                        html, re.IGNORECASE
                    )),
                }

            # API-first path
            repo_info, repo_code = fetch_api(f"repos/{owner}/{repo}")
            if repo_code == 404:
                return json.dumps({
                    "health_score": 0,
                    "error": "repository not found (404)",
                    "owner": owner,
                    "repo": repo,
                })

            api_data = None
            if isinstance(repo_info, dict):
                commits, _ = fetch_api(f"repos/{owner}/{repo}/commits?per_page=1")
                readme, _ = fetch_api(f"repos/{owner}/{repo}/readme")
                root, _ = fetch_api(f"repos/{owner}/{repo}/contents/")
                workflows, _ = fetch_api(f"repos/{owner}/{repo}/contents/.github/workflows")

                is_empty = commits == []
                last_commit_ts = None
                if isinstance(commits, list) and len(commits) > 0:
                    try:
                        last_commit_ts = commits[0]["commit"]["committer"]["date"]
                    except (KeyError, TypeError):
                        try:
                            last_commit_ts = commits[0]["commit"]["author"]["date"]
                        except (KeyError, TypeError):
                            pass

                ci_files = {
                    ".travis.yml", ".drone.yml", "azure-pipelines.yml",
                    ".gitlab-ci.yml", "bitbucket-pipelines.yml", "Jenkinsfile",
                    "Makefile",
                }
                ci_dirs = {".circleci", ".github"}
                has_ci = False
                if isinstance(root, list):
                    names = {str(item.get("name", "")) for item in root}
                    has_ci = bool((names & ci_files) or (names & ci_dirs))
                if not has_ci:
                    has_ci = isinstance(workflows, list) and len(workflows) > 0

                api_data = {
                    "is_empty": is_empty,
                    "last_commit_ts": last_commit_ts,
                    "open_issues_count": repo_info.get("open_issues_count", 0),
                    "has_license": repo_info.get("license") is not None,
                    "is_fork": bool(repo_info.get("fork", False)),
                    "has_readme": isinstance(readme, dict) and "name" in readme,
                    "has_ci": has_ci,
                }

            # HTML fallback/augmentation path
            html_resp = http_get(page_url)
            html = decode_body(html_resp)
            html_data = parse_html_signals(html)

            if api_data is None and html_data is None:
                return json.dumps({
                    "health_score": previous_score,
                    "error": "all data sources failed; returned cached score",
                    "owner": owner,
                    "repo": repo,
                    "used_cached_score": True,
                })

            # Prefer API, fill gaps from HTML if API path is partially missing.
            if api_data is None:
                data = html_data
            elif html_data is None:
                data = api_data
            else:
                data = dict(api_data)
                for key, value in html_data.items():
                    if key not in data:
                        data[key] = value
                if not data.get("last_commit_ts") and html_data.get("last_commit_ts"):
                    data["last_commit_ts"] = html_data["last_commit_ts"]
                if not data.get("has_readme", False):
                    data["has_readme"] = html_data.get("has_readme", False)
                if not data.get("has_ci", False):
                    data["has_ci"] = html_data.get("has_ci", False)
                if not data.get("has_license", False):
                    data["has_license"] = html_data.get("has_license", False)
                if not data.get("is_fork", False):
                    data["is_fork"] = html_data.get("is_fork", False)
                if int(data.get("open_issues_count") or 0) == 0 and int(html_data.get("open_issues_count") or 0) > 0:
                    data["open_issues_count"] = html_data["open_issues_count"]
                if bool(data.get("is_empty")) and not html_data.get("is_empty", True):
                    data["is_empty"] = False

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
