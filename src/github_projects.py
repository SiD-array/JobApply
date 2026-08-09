"""
GitHub Projects Integration & Synchronization Service.
Queries SiD-array's public repositories, auto-updates the local projects_library.json database
using LLM-generated bullet points if a new commit is detected, and dynamically selects
the best-matching projects for a target job description.
"""

import sys
import os
import json
import requests
import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

LIBRARY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "projects_library.json"))
COOLDOWN_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".api_cooldowns.json"))

# Projects to explicitly ignore (basic or pipeline code)
IGNORED_REPOS = {
    "Clock", "Currency-converter", "To-do-list", "weather-app", "sudoku-puzzle",
    "portfolio", "SiD-array", "JobApply", "Overview_Analysis", "Test-Filtering-Workflow"
}

GENERATE_BULLET_PROMPT = """You are a professional resume writer.
Your task is to write 3 high-quality, impact-driven resume bullet points for a project using the Google X-Y-Z formula:
"Accomplished [X] as measured by [Y], by doing [Z]"

If the README contains metrics, prioritize them. If not, formulate strong technical achievements.

PROJECT NAME: {name}
PROJECT DESCRIPTION: {description}
PROJECT README CONTENT:
{readme}

Return RAW VALID JSON ONLY matching this exact schema:
{{
  "bullet_points": ["string", "string", "string"],
  "technologies": ["string"]
}}
"""

SELECT_PROJECTS_PROMPT = """You are a Technical Recruiter matching a candidate's projects to a job description.
From the list of candidate projects below, select the top {limit} projects that are most relevant to the target job.
If 'SignLens-RealTime-ASL-Recognition' is one of the options, only select it as a fallback if there are not enough other highly relevant projects.

CANDIDATE PROJECTS:
{projects_summary}

TARGET JOB DESCRIPTION:
{job_desc}

Return RAW VALID JSON ONLY matching this exact schema:
{{
  "selected_projects": ["project_key_1", "project_key_2"]
}}
"""


class GitHubProjectsManager:
    """Manager for fetching GitHub repos, updating projects_library.json, and selecting aligned projects."""

    def __init__(self, provider: str = "ollama"):
        self.provider = provider.lower()

    def fetch_github_repos(self) -> List[Dict[str, Any]]:
        """Fetch public repositories for SiD-array from the GitHub API."""
        url = "https://api.github.com/users/SiD-array/repos"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        # Support GitHub token to prevent API rate limiting
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token.strip()}"

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.json()
            else:
                print(f"[GITHUB API WARNING] Failed to fetch repositories: Status {res.status_code}", file=sys.stderr)
                return []
        except Exception as e:
            print(f"[GITHUB API ERROR] Connection failed: {e}", file=sys.stderr)
            return []

    def fetch_readme(self, repo_name: str, default_branch: str = "main") -> str:
        """Fetch raw README.md for a given repository."""
        branches = [default_branch, "master", "dev"]
        headers = {"User-Agent": "Mozilla/5.0"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token.strip()}"

        for b in branches:
            url = f"https://raw.githubusercontent.com/SiD-array/{repo_name}/{b}/README.md"
            try:
                res = requests.get(url, headers=headers, timeout=8)
                if res.status_code == 200:
                    return res.text
            except Exception:
                pass
        return ""

    def update_projects_library(self):
        """Scan GitHub repositories and update projects_library.json if new commits are found."""
        if not os.path.exists(LIBRARY_PATH):
            print(f"[PROJECT LIBRARY] Library file not found at {LIBRARY_PATH}. Creating empty library.", file=sys.stderr)
            library = {}
        else:
            with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
                library = json.load(f)

        repos = self.fetch_github_repos()
        if not repos:
            print("[PROJECT LIBRARY] No repositories fetched. Skipping synchronization.", file=sys.stderr)
            return

        library_changed = False

        for repo in repos:
            name = repo.get("name")
            if name in IGNORED_REPOS:
                continue

            pushed_at = repo.get("pushed_at")  # Time of last commit/push
            default_branch = repo.get("default_branch", "main")
            description = repo.get("description") or ""

            # Check if project exists in local library and needs an update
            existing_entry = library.get(name)
            needs_update = False

            if not existing_entry:
                needs_update = True
                print(f"[SYNC] New repository discovered on GitHub: '{name}'", file=sys.stderr)
            else:
                last_updated = existing_entry.get("last_updated")
                if not last_updated or pushed_at > last_updated:
                    needs_update = True
                    print(f"[SYNC] Update/New commit detected for repository: '{name}' (pushed_at: {pushed_at})", file=sys.stderr)

            if needs_update:
                readme_content = self.fetch_readme(name, default_branch)
                if not readme_content and not description:
                    # No description or README, skip generating
                    continue

                # Generate new bullet points using LLM
                print(f"[SYNC] Generating/Updating bullet points for '{name}'...", file=sys.stderr)
                try:
                    generated = self._generate_bullet_points(name, description, readme_content[:4000])
                    bullets = generated.get("bullet_points", [])
                    techs = generated.get("technologies") or repo.get("topics") or [repo.get("language")]
                    techs = [t for t in techs if t]  # filter nulls
                    
                    if not bullets:
                        raise ValueError("LLM returned empty bullet points")

                    # Preserve priority if exists, default to 2
                    priority = existing_entry.get("priority", 2) if existing_entry else 2

                    # Preserve date if exists, default to repo created date
                    created_at = repo.get("created_at")
                    date_str = created_at[:7] if created_at else datetime.datetime.now().strftime("%Y-%m")
                    date_val = existing_entry.get("date") if existing_entry else date_str

                    library[name] = {
                        "name": existing_entry.get("name", name.replace("-", " ").title()) if existing_entry else name.replace("-", " ").title(),
                        "description": description,
                        "technologies": techs,
                        "bullet_points": bullets,
                        "priority": priority,
                        "github_repo": name,
                        "last_updated": pushed_at,
                        "date": date_val
                    }
                    library_changed = True
                    print(f"[SYNC SUCCESS] Updated local library details for: {name}", file=sys.stderr)
                except Exception as e:
                    print(f"[SYNC WARNING] Failed generating details for '{name}': {e}", file=sys.stderr)

        if library_changed:
            with open(LIBRARY_PATH, "w", encoding="utf-8") as f:
                json.dump(library, f, indent=2)
            print("[SYNC COMPLETE] Saved updated projects_library.json", file=sys.stderr)
        else:
            print("[SYNC COMPLETE] No repository updates required.", file=sys.stderr)

    def select_best_projects(self, job: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        """Select top 3 most relevant projects from projects_library.json aligning with the target job."""
        if not os.path.exists(LIBRARY_PATH):
            print("[EVALUATE] projects_library.json not found. Returning empty projects list.", file=sys.stderr)
            return []

        with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
            library = json.load(f)

        if not library:
            return []

        # Build list of projects summaries for the LLM selection prompt
        projects_summary = []
        for key, proj in library.items():
            projects_summary.append({
                "project_key": key,
                "name": proj.get("name"),
                "description": proj.get("description"),
                "technologies": proj.get("technologies"),
                "priority": proj.get("priority", 2)
            })

        job_title = job.get("title", "Target Position")
        job_company = job.get("company", "Target Company")
        job_desc = job.get("description", "")
        job_text = f"Title: {job_title}\nCompany: {job_company}\nDescription:\n{job_desc}"

        user_prompt = f"""
CANDIDATE PROJECTS:
{json.dumps(projects_summary, indent=2)}

TARGET JOB DESCRIPTION:
{job_text}
"""

        print(f"\n[AI PROJECT SELECTION] Querying LLM to choose the best {limit} projects...", file=sys.stderr)
        
        selected_keys = []
        try:
            # Call LLM to select best matching keys
            res_dict = self._execute_llm(SELECT_PROJECTS_PROMPT.format(limit=limit, projects_summary=json.dumps(projects_summary, indent=2), job_desc=job_text), user_prompt)
            selected_keys = res_dict.get("selected_projects", [])
        except Exception as e:
            print(f"[AI PROJECT SELECTION WARNING] LLM selection failed: {e}. Falling back to default priority selection.", file=sys.stderr)
            # Default fallback: Sort by priority, then get first 'limit' items
            sorted_projects = sorted(library.items(), key=lambda x: (x[1].get("priority", 2), x[0]))
            selected_keys = [item[0] for item in sorted_projects[:limit]]

        # Map back to full project details
        selected_projects = []
        for k in selected_keys:
            if k in library:
                proj_data = library[k]
                selected_projects.append({
                    "name": proj_data.get("name"),
                    "technologies": proj_data.get("technologies"),
                    "bullet_points": proj_data.get("bullet_points"),
                    "date": proj_data.get("date", "")
                })

        # Ensure we always return at least the requested limit if we have enough projects
        if len(selected_projects) < limit:
            for k, proj_data in library.items():
                if k not in selected_keys and len(selected_projects) < limit:
                    selected_projects.append({
                        "name": proj_data.get("name"),
                        "technologies": proj_data.get("technologies"),
                        "bullet_points": proj_data.get("bullet_points"),
                        "date": proj_data.get("date", "")
                    })

        print(f"[AI PROJECT SELECTION] Featured projects: {', '.join([p['name'] for p in selected_projects])}", file=sys.stderr)
        return selected_projects

    def _generate_bullet_points(self, name: str, description: str, readme: str) -> dict:
        """Call LLM to generate professional bullet points for a project README."""
        system_prompt = GENERATE_BULLET_PROMPT.format(name=name, description=description, readme=readme)
        user_prompt = f"Write bullet points for project {name}."
        return self._execute_llm(system_prompt, user_prompt)

    def _execute_llm(self, system_prompt: str, user_prompt: str) -> dict:
        """Helper to call LLM with fallback support."""
        order = []
        if self.provider:
            order.append(self.provider)
        for p in ["ollama", "groq", "openrouter"]:
            if p not in order:
                order.append(p)

        last_err = None
        for p in order:
            if self._is_on_cooldown(p):
                continue
            try:
                if p == "ollama":
                    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
                    url = f"{base_url.rstrip('/')}/v1/chat/completions"
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                    res = requests.post(url, json=payload, timeout=120)
                    if res.status_code == 200:
                        return json.loads(res.json()["choices"][0]["message"]["content"])
                    raise RuntimeError(f"Ollama Error: {res.text}")

                elif p == "groq":
                    api_key = os.getenv("GROQ_API_KEY")
                    if not api_key:
                        raise ValueError("GROQ_API_KEY not set")
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
                    payload = {
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                    res = requests.post(url, headers=headers, json=payload, timeout=25)
                    if res.status_code == 200:
                        return json.loads(res.json()["choices"][0]["message"]["content"])
                    raise RuntimeError(f"Groq Error: {res.text}")

                elif p == "openrouter":
                    api_key = os.getenv("OPENROUTER_API_KEY")
                    url = "https://openrouter.ai/api/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
                    payload = {
                        "model": "google/gemma-4-31b-it:free",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                    res = requests.post(url, headers=headers, json=payload, timeout=30)
                    if res.status_code == 200:
                        return json.loads(res.json()["choices"][0]["message"]["content"])
                    raise RuntimeError(f"OpenRouter Error: {res.text}")

            except Exception as e:
                print(f"[LLM WARNING] Provider {p.upper()} failed: {e}", file=sys.stderr)
                self._set_cooldown(p)
                last_err = e

        raise RuntimeError(f"All LLM providers failed. Last error: {last_err}")

    def _is_on_cooldown(self, provider: str) -> bool:
        if provider == "ollama":
            return False
        try:
            if os.path.exists(COOLDOWN_FILE):
                with open(COOLDOWN_FILE, "r") as f:
                    data = json.load(f)
                fail_time = data.get(provider, 0)
                if time.time() - fail_time < 7200:  # 2 hours
                    return True
        except Exception:
            pass
        return False

    def _set_cooldown(self, provider: str):
        if provider == "ollama":
            return
        try:
            data = {}
            if os.path.exists(COOLDOWN_FILE):
                with open(COOLDOWN_FILE, "r") as f:
                    data = json.load(f)
            data[provider] = time.time()
            with open(COOLDOWN_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Synchronize and Select GitHub Projects CLI")
    parser.add_argument("--sync", action="store_true", help="Sync local projects_library.json with GitHub repos")
    parser.add_argument("--select", action="store_true", help="Select best projects for target job")
    parser.add_argument("--job", help="Path to job JSON file")
    parser.add_argument("--provider", default="ollama", help="AI Provider for updates/selection")
    args = parser.parse_args()

    manager = GitHubProjectsManager(provider=args.provider)

    if args.sync:
        print("[SYNC] Running GitHub Repository Synchronization...")
        manager.update_projects_library()

    if args.select:
        if not args.job or not os.path.exists(args.job):
            print("Error: --job JSON path required for selection.")
            sys.exit(1)
        with open(args.job, "r", encoding="utf-8") as f:
            job_data = json.load(f)
        selected = manager.select_best_projects(job_data)
        print("\nSelected Projects JSON:")
        print(json.dumps(selected, indent=2))


if __name__ == "__main__":
    main()
