# v0.3.0
# { "Depends": "py-genlayer:latest" }

import json
import re
from datetime import datetime, timezone

from genlayer import *


class GitHealth(gl.Contract):
    """
    GitHub repository health analyzer.

    Design goals:
    - API-first (GitHub REST), status-code driven decisions.
    - Conservative fallback behavior when sources are partially unavailable.
    - Deterministic normalization before scoring.
    - Robust handling of non-existent repos and malformed inputs.
    """

    repo_scores: TreeMap[str, u256]
    repo_details: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def analyze_repo(self, repo_url: str) -> int:
        def normalize_repo_url(url) -> tuple[str, str, str]:
            if not isinstance(url, str):
                raise ValueError("repo_url must be a string")
            raw = url.strip()
            if not raw:
                raise ValueError("repo_url is empty")

            raw = raw.replace("git@github.com:", "https://github.com/")
            if raw.startswith("github.com/"):
                raw = f"https://{raw}"

            # Accept GitHub URL with optional scheme, query, fragment and subpaths.
            m = re.match(
                r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s#?]+)",
                raw,
                re.IGNORECASE,
            )
            if not m:
                raise ValueError(f"invalid github repo url: {raw!r}")

            owner = m.group(1).strip()
            repo = m.group(2).strip()
            if repo.endswith(".git"):
                repo = repo[:-4]
            if not owner or not repo:
                raise ValueError("invalid owner/repo")

            canonical = f"https://github.com/{owner}/{repo}"
            return owner, repo, canonical

        def days_since(iso_ts: str):
            if not iso_ts:
                return None
            try:
                dt = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
                return max(0, (datetime.now(timezone.utc) - dt).days)
            except Exception:
                return None

        def clamp_score(score: int) -> int:
            return max(0, min(100, score))

        def compute_score(payload: dict) -> tuple[int, dict]:
            score = 100
            out = {}

            is_empty = bool(payload.get("is_empty", False))
            last_commit_ts = str(payload.get("last_commit_ts") or "")
            open_issues = max(0, int(payload.get("open_issues_count") or 0))
            has_readme = bool(payload.get("has_readme", False))
            has_ci = bool(payload.get("has_ci", False))
            has_license = bool(payload.get("has_license", False))
            is_fork = bool(payload.get("is_fork", False))
            is_archived = bool(payload.get("is_archived", False))
            is_disabled = bool(payload.get("is_disabled", False))

            out["is_empty"] = is_empty
            out["last_commit_ts"] = last_commit_ts
            out["open_issues"] = open_issues
            out["has_readme"] = has_readme
            out["has_ci"] = has_ci
            out["has_license"] = has_license
            out["is_fork"] = is_fork
            out["is_archived"] = is_archived
            out["is_disabled"] = is_disabled

            if is_empty:
                recency_penalty = 65
                empty_penalty = 20
                days = None
            else:
                empty_penalty = 0
                days = days_since(last_commit_ts)
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

            issue_penalty = min(20, open_issues // 10)
            trust_penalty = 0
            if not has_readme:
                trust_penalty += 5
            if not has_ci:
                trust_penalty += 5
            if not has_license:
                trust_penalty += 5

            fork_penalty = 5 if is_fork else 0
            archived_penalty = 10 if is_archived else 0
            disabled_penalty = 10 if is_disabled else 0

            total_penalty = (
                recency_penalty
                + empty_penalty
                + issue_penalty
                + trust_penalty
                + fork_penalty
                + archived_penalty
                + disabled_penalty
            )
            score = clamp_score(score - total_penalty)

            out["days_since_last_commit"] = days
            out["recency_penalty"] = recency_penalty
            out["empty_penalty"] = empty_penalty
            out["issue_penalty"] = issue_penalty
            out["trust_penalty"] = trust_penalty
            out["fork_penalty"] = fork_penalty
            out["archived_penalty"] = archived_penalty
            out["disabled_penalty"] = disabled_penalty
            out["total_penalty"] = total_penalty
            out["health_score"] = score
            return score, out

        def safe_int(value, default=0):
            try:
                return int(value)
            except Exception:
                return default

        def parse_html_signals(html: str) -> dict | None:
            if not html:
                return None

            is_empty_html = bool(
                re.search(r"(This repository is empty|no commits yet)", html, re.IGNORECASE)
            )

            last_commit_html = None
            ts_match = re.search(
                r'datetime="(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"', html
            )
            if ts_match:
                last_commit_html = ts_match.group(1)

            issues = 0
            issues_match = re.search(
                r"Issues.*?Counter[^>]*>\s*([\d,]+)\s*</span>", html, re.DOTALL | re.IGNORECASE
            )
            if issues_match:
                try:
                    issues = int(issues_match.group(1).replace(",", ""))
                except ValueError:
                    issues = 0

            has_license = bool(
                re.search(
                    r"(View license|MIT License|Apache License|BSD License|GPL|LGPL|ISC License|Unlicense)",
                    html,
                    re.IGNORECASE,
                )
            )
            has_ci = bool(
                re.search(
                    r"(\.github/workflows|travis-ci\.com|travis-ci\.org|circleci\.com|azure-pipelines|Jenkinsfile)",
                    html,
                    re.IGNORECASE,
                )
            )
            has_readme = bool(re.search(r"README", html))
            is_fork = bool(re.search(r"forked from", html, re.IGNORECASE))

            return {
                "is_empty": is_empty_html,
                "last_commit_ts": last_commit_html,
                "open_issues_count": issues,
                "has_license": has_license,
                "has_ci": has_ci,
                "has_readme": has_readme,
                "is_fork": is_fork,
            }

        try:
            owner, repo, canonical_repo_url = normalize_repo_url(repo_url)
        except Exception as exc:
            payload = {
                "health_score": 0,
                "error": f"invalid repo url: {exc}",
                "repo_url": str(repo_url),
            }
            self.repo_scores[str(repo_url)] = u256(0)
            self.repo_details[str(repo_url)] = json.dumps(payload)
            return 0

        page_url = canonical_repo_url
        api_base = "https://api.github.com"
        previous_score = int(self.repo_scores[canonical_repo_url]) if canonical_repo_url in self.repo_scores else 0

        def collect_repo_health() -> str:
            def http_get(url: str):
                try:
                    return gl.nondet.web.get(url)
                except Exception:
                    return None

            def decode_body(resp) -> str:
                if resp is None:
                    return ""
                raw = getattr(resp, "body", None)
                if isinstance(raw, bytes):
                    return raw.decode("utf-8", errors="replace")
                if isinstance(raw, str):
                    return raw
                text = getattr(resp, "text", None)
                if isinstance(text, str):
                    return text
                data = getattr(resp, "data", None)
                if isinstance(data, bytes):
                    return data.decode("utf-8", errors="replace")
                if isinstance(data, str):
                    return data
                return ""

            def status_code(resp) -> int:
                if resp is None:
                    return 0
                return safe_int(getattr(resp, "status_code", None) or getattr(resp, "status", None), 0)

            def fetch_api(path: str):
                resp = http_get(f"{api_base}/{path}")
                code = status_code(resp)
                body = decode_body(resp)

                if code == 409:
                    return [], code
                if code == 404:
                    return None, 404
                if code >= 400:
                    return None, code

                try:
                    parsed = json.loads(body)
                except Exception:
                    return None, code

                if isinstance(parsed, dict) and "message" in parsed and "id" not in parsed:
                    msg = str(parsed.get("message", ""))
                    if "empty" in msg.lower():
                        return [], code
                return parsed, code

            repo_info, repo_code = fetch_api(f"repos/{owner}/{repo}")
            if repo_code == 404:
                return json.dumps(
                    {
                        "health_score": 0,
                        "error": "repository not found",
                        "owner": owner,
                        "repo": repo,
                        "canonical_repo_url": canonical_repo_url,
                    },
                    sort_keys=True,
                )

            # HTML status 404 is only considered authoritative when API data is unavailable.
            html_resp = http_get(page_url)
            html_code = status_code(html_resp)
            html_data = parse_html_signals(decode_body(html_resp))

            if repo_info is None and html_code == 404:
                return json.dumps(
                    {
                        "health_score": 0,
                        "error": "repository not found",
                        "owner": owner,
                        "repo": repo,
                        "canonical_repo_url": canonical_repo_url,
                        "source": "html_status_404",
                    },
                    sort_keys=True,
                )

            api_data = None
            source_status = {
                "repo_api_status": repo_code,
                "html_status": html_code,
            }

            if isinstance(repo_info, dict):
                commits, commits_code = fetch_api(f"repos/{owner}/{repo}/commits?per_page=1")
                readme, readme_code = fetch_api(f"repos/{owner}/{repo}/readme")
                root, root_code = fetch_api(f"repos/{owner}/{repo}/contents/")
                workflows, workflows_code = fetch_api(f"repos/{owner}/{repo}/contents/.github/workflows")

                source_status["commits_api_status"] = commits_code
                source_status["readme_api_status"] = readme_code
                source_status["root_api_status"] = root_code
                source_status["workflows_api_status"] = workflows_code

                repo_size = safe_int(repo_info.get("size"), 0)
                default_branch = str(repo_info.get("default_branch") or "").strip()
                commits_empty_list = isinstance(commits, list) and len(commits) == 0
                is_empty = commits_code == 409 or (commits_empty_list and repo_size == 0)
                if not default_branch and (commits_code in (200, 409, None)):
                    is_empty = True
                last_commit_ts = ""
                if isinstance(commits, list) and commits:
                    first = commits[0] if isinstance(commits[0], dict) else {}
                    commit = first.get("commit", {}) if isinstance(first, dict) else {}
                    committer = commit.get("committer", {}) if isinstance(commit, dict) else {}
                    author = commit.get("author", {}) if isinstance(commit, dict) else {}
                    last_commit_ts = str(committer.get("date") or author.get("date") or "")

                pushed_at = str(repo_info.get("pushed_at") or "")
                if not last_commit_ts and pushed_at and not is_empty:
                    last_commit_ts = pushed_at

                if is_empty and last_commit_ts:
                    is_empty = False

                ci_files = {
                    ".travis.yml",
                    ".drone.yml",
                    "azure-pipelines.yml",
                    ".gitlab-ci.yml",
                    "bitbucket-pipelines.yml",
                    "Jenkinsfile",
                    "Makefile",
                    "buildkite.yml",
                }
                ci_dirs = {".circleci", ".github"}

                has_ci = False
                if isinstance(root, list):
                    names = {str(item.get("name", "")) for item in root if isinstance(item, dict)}
                    if names & ci_files:
                        has_ci = True
                    if names & ci_dirs:
                        has_ci = True
                if not has_ci:
                    has_ci = isinstance(workflows, list) and len(workflows) > 0

                has_readme = False
                if isinstance(readme, dict):
                    name = str(readme.get("name", "")).lower()
                    has_readme = name.startswith("readme")

                api_data = {
                    "is_empty": bool(is_empty),
                    "last_commit_ts": last_commit_ts,
                    "open_issues_count": safe_int(repo_info.get("open_issues_count"), 0),
                    "has_license": repo_info.get("license") is not None,
                    "is_fork": bool(repo_info.get("fork", False)),
                    "has_readme": has_readme,
                    "has_ci": has_ci,
                    "is_archived": bool(repo_info.get("archived", False)),
                    "is_disabled": bool(repo_info.get("disabled", False)),
                }

            if api_data is None and html_data is None:
                return json.dumps(
                    {
                        "health_score": previous_score,
                        "error": "all data sources failed; returned cached score",
                        "owner": owner,
                        "repo": repo,
                        "canonical_repo_url": canonical_repo_url,
                        "used_cached_score": True,
                        "source_status": source_status,
                    },
                    sort_keys=True,
                )

            if api_data is None:
                merged = dict(html_data)
                merged["is_archived"] = False
                merged["is_disabled"] = False
                merged["source"] = "html_only"
            elif html_data is None:
                merged = dict(api_data)
                merged["source"] = "api_only"
            else:
                merged = dict(api_data)
                merged["source"] = "api_plus_html"

                if not merged.get("last_commit_ts") and html_data.get("last_commit_ts"):
                    merged["last_commit_ts"] = html_data.get("last_commit_ts")
                if not merged.get("has_readme", False):
                    merged["has_readme"] = bool(html_data.get("has_readme", False))
                if not merged.get("has_ci", False):
                    merged["has_ci"] = bool(html_data.get("has_ci", False))
                if not merged.get("has_license", False):
                    merged["has_license"] = bool(html_data.get("has_license", False))
                if not merged.get("is_fork", False):
                    merged["is_fork"] = bool(html_data.get("is_fork", False))

                api_issues = safe_int(merged.get("open_issues_count"), 0)
                html_issues = safe_int(html_data.get("open_issues_count"), 0)
                if api_issues == 0 and html_issues > 0:
                    merged["open_issues_count"] = html_issues

                if merged.get("is_empty") and (merged.get("last_commit_ts") or not html_data.get("is_empty", True)):
                    merged["is_empty"] = False

            score, breakdown = compute_score(merged)
            breakdown["owner"] = owner
            breakdown["repo"] = repo
            breakdown["canonical_repo_url"] = canonical_repo_url
            breakdown["source"] = merged.get("source", "unknown")
            breakdown["source_status"] = source_status
            return json.dumps(breakdown, sort_keys=True)

        final_json_str = gl.eq_principle.prompt_comparative(
            collect_repo_health,
            """
            Compare all returned JSON objects by health_score.
            Accept only when all health_score values are within 5 points.
            If accepted, return the object with the lowest health_score.
            """,
        )

        parsed = json.loads(final_json_str)
        score = safe_int(parsed.get("health_score"), 0)
        score = clamp_score(score)

        self.repo_scores[canonical_repo_url] = u256(score)
        self.repo_details[canonical_repo_url] = json.dumps(parsed, sort_keys=True)

        # Backward compatibility: preserve lookup by raw user input as well.
        self.repo_scores[str(repo_url)] = u256(score)
        self.repo_details[str(repo_url)] = json.dumps(parsed, sort_keys=True)
        return score

    @gl.public.view
    def get_score(self, repo_url: str) -> int:
        if repo_url in self.repo_scores:
            return int(self.repo_scores[repo_url])
        return 0

    @gl.public.view
    def get_details(self, repo_url: str) -> str:
        if repo_url in self.repo_details:
            return self.repo_details[repo_url]
        return "{}"
