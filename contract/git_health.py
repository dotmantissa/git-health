# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json

from genlayer import *


class GitHealth(gl.Contract):
    """
    Analyzes GitHub repositories to assign a "Health Score" (0-100) based on
    maintenance activity visible on the main page.
    """

    # Maps Repository URL (str) -> Health Score (u256)
    repo_scores: TreeMap[str, u256]

    def __init__(self):
        pass

    @gl.public.write
    def analyze_repo(self, repo_url: str) -> int:
        """
        Scrapes a GitHub repository, calculates a health score based on recent
        commits and open issues, and updates the state.
        """

        def compute_score(parsed: dict) -> int:
            score = 100

            last_commit_text = str(parsed.get("last_commit_text", "")).strip().lower()
            recency_bucket = str(parsed.get("commit_recency_bucket", "")).strip().lower()
            confidence = str(parsed.get("confidence", "")).strip().lower()
            issues_count_raw = parsed.get("open_issues_count", 0)

            # Penalize uncertainty by default if commit recency is missing or ambiguous.
            if not last_commit_text or recency_bucket not in {
                "within_1_month",
                "over_1_month",
                "over_6_months",
                "over_1_year",
            }:
                score -= 10
            elif recency_bucket == "over_1_month":
                score -= 10
            elif recency_bucket == "over_6_months":
                score -= 40
            elif recency_bucket == "over_1_year":
                score -= 60

            try:
                issues_count = int(issues_count_raw)
            except Exception:
                issues_count = 0

            if issues_count < 0:
                issues_count = 0
            issue_deduction = min(20, issues_count // 10)
            score -= issue_deduction

            if score < 0:
                score = 0

            # Require explicit commit evidence for a perfect score.
            if score == 100 and not last_commit_text:
                score = 90

            # Low confidence prevents optimistic high scoring.
            if confidence == "low" and score > 90:
                score = 90

            return score

        def get_repo_health():
            # 1. Fetch the repo page
            try:
                print(f"Fetching {repo_url}...")
                web_content = gl.nondet.web.render(repo_url, mode="text")
            except Exception as e:
                print(f"Fetch failed: {e}")
                # Return a valid JSON structure even on failure so the parser doesn't break
                return json.dumps({"health_score": 0, "reasoning": "Fetch failed"})

            # 2. LLM Analysis Task
            task = f"""
            You are a Code Repository Auditor.
            Extract structured evidence from this GitHub page text.

            Rules:
            - Only use information explicitly visible in the provided text.
            - If a field is missing or ambiguous, return empty text and low confidence.
            - Do not infer hidden values.
            - Prefer explicit recency snippets like:
              "committed X days ago", "updated on Month Day, Year",
              "Latest commit", "last commit".
            - For open issues, prefer visible tab counts near "Issues".

            Return ONLY valid JSON with this exact schema:
            {{
              "last_commit_text": "verbatim commit recency evidence or empty string",
              "commit_recency_bucket": "within_1_month|over_1_month|over_6_months|over_1_year|unknown",
              "open_issues_text": "verbatim open issues evidence or empty string",
              "open_issues_count": 0,
              "confidence": "high|medium|low",
              "reasoning": "short rationale for extracted evidence"
            }}

            Repo Content Snippet:
            {web_content[:6000]}
            """

            # 3. Execute Prompt
            result_raw = gl.nondet.exec_prompt(task)
            cleaned = result_raw.replace("```json", "").replace("```", "").strip()
            print(f"LLM Extraction: {cleaned}")

            try:
                extracted = json.loads(cleaned)
            except Exception:
                extracted = {
                    "last_commit_text": "",
                    "commit_recency_bucket": "unknown",
                    "open_issues_text": "",
                    "open_issues_count": 0,
                    "confidence": "low",
                    "reasoning": "Extraction parse failed",
                }

            # Focused second pass for commit recency when initial extraction is weak.
            if (
                not str(extracted.get("last_commit_text", "")).strip()
                or str(extracted.get("commit_recency_bucket", "")).strip().lower()
                == "unknown"
            ):
                recency_task = f"""
                Extract ONLY commit recency evidence from this GitHub page text.
                Use exact visible phrasing where possible.

                Return ONLY valid JSON:
                {{
                  "last_commit_text": "verbatim recency phrase or empty string",
                  "commit_recency_bucket": "within_1_month|over_1_month|over_6_months|over_1_year|unknown",
                  "confidence": "high|medium|low"
                }}

                Repo Content Snippet:
                {web_content[:6000]}
                """
                recency_raw = gl.nondet.exec_prompt(recency_task)
                recency_cleaned = (
                    recency_raw.replace("```json", "").replace("```", "").strip()
                )
                print(f"LLM Recency Extraction: {recency_cleaned}")

                try:
                    recency_extracted = json.loads(recency_cleaned)
                    if str(recency_extracted.get("last_commit_text", "")).strip():
                        extracted["last_commit_text"] = recency_extracted.get(
                            "last_commit_text", ""
                        )
                    if str(recency_extracted.get("commit_recency_bucket", "")).strip():
                        extracted["commit_recency_bucket"] = recency_extracted.get(
                            "commit_recency_bucket", "unknown"
                        )
                    # Keep the lower confidence between passes.
                    existing_conf = str(extracted.get("confidence", "low")).lower()
                    second_conf = str(recency_extracted.get("confidence", "low")).lower()
                    if existing_conf == "low" or second_conf == "low":
                        extracted["confidence"] = "low"
                    elif existing_conf == "medium" or second_conf == "medium":
                        extracted["confidence"] = "medium"
                    else:
                        extracted["confidence"] = "high"
                except Exception:
                    pass

            score = compute_score(extracted)
            extracted["health_score"] = score
            extracted["evidence_missing"] = not bool(
                str(extracted.get("last_commit_text", "")).strip()
            )
            return json.dumps(extracted)

        # 4. Comparative Consensus
        # FIX: Passed as a positional argument (removed 'criteria=')
        consensus_instruction = """
        Compare the 'health_score' values in the JSON results.
        They must be effectively equal, defined as being within a difference of 5 points.
        (e.g. 80 and 85 are valid matches. 80 and 86 are not).
        """

        final_json_str = gl.eq_principle.prompt_comparative(
            get_repo_health, consensus_instruction
        )

        # 5. Parse and Store
        parsed = json.loads(final_json_str)
        score = int(parsed["health_score"])

        self.repo_scores[repo_url] = u256(score)
        return score

    @gl.public.view
    def get_score(self, repo_url: str) -> int:
        if repo_url in self.repo_scores:
            return int(self.repo_scores[repo_url])
        return 0
