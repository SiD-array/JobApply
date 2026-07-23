#!/usr/bin/env python3
"""
Stage 2: AI-Powered Technical Recruiter Evaluator
Replaces keyword matching with LLM reasoning (Groq Llama 3.3 70B / Cerebras / OpenRouter / Gemini).
Evaluates job postings against candidate profile for Role Match, Skill Match,
Experience Level, Exclusions, and Interview Probability.
"""

import sys
import os
import json
import argparse
import requests
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

RECRUITER_SYSTEM_PROMPT = """You are an experienced Technical Recruiter hiring for AI, Software Engineering, and Machine Learning positions.
Your task is to evaluate whether a supplied job posting is a strong fit for the candidate profile.

CANDIDATE PROFILE:
- Education: M.S. Computer Science @ Rochester Institute of Technology (RIT), GPA: 3.82 (Graduation: May 2027)
- Current Role: DAAD RISE Professional Scholar - AI Engineering Intern @ BSH Hausgeräte GmbH (Bosch Group)
- Previous Role: Machine Learning Intern @ Verzeo EduTech
- Core Skills: Python, Java, C++, TensorFlow, PyTorch, FastAPI, React, AWS, Computer Vision, Machine Learning, Cloud Computing, Backend Development, PostgreSQL, Docker, Git
- Primary Target Roles: Software Engineer, AI Software Engineer, Machine Learning Engineer, Applied AI Engineer, Backend Software Engineer, AI Platform Engineer, Cloud Engineer, Computer Vision Engineer, Embedded AI Engineer, Data Engineer
- Desired Seniority: Entry Level, New Grad, University Graduate, Campus Hire, Associate, Early Career (0-2 years preferred, 3 years acceptable)

AUTOMATIC REJECTION CRITERIA (Set recommendation="REJECT", interviewProbability="Low", score <= 40):
1. Requires 5+ years of experience.
2. Seniority is Senior, Staff, Principal, Lead, Manager, Director, or Architect.
3. Requires Active Security Clearance or US Citizenship (candidate requires OPT/CPT sponsorship).
4. Pure frontend-only, pure mobile (iOS/Android)-only, QA-only, DevOps-only, Sales, or IT Support roles.

EVALUATION WEIGHTS:
- Role Match (30 pts): Alignment with target roles.
- Skill Match (25 pts): Deep technical overlap (Python, PyTorch, TensorFlow, AWS, FastAPI, ML, Backend).
- Experience Match (15 pts): Relevance of Bosch AI internship, ML internship, and AI projects.
- Career Level (15 pts): 0-2 years (Highest), 3 years (Acceptable).
- Company Reputation & Growth Potential (15 pts).

OUTPUT INSTRUCTIONS:
Return RAW VALID JSON ONLY matching this exact schema:
{
  "score": integer (0-100),
  "interviewProbability": "High" | "Medium" | "Low",
  "matchedRole": "string",
  "matchedSkills": ["string"],
  "missingSkills": ["string"],
  "strengths": ["string"],
  "weaknesses": ["string"],
  "reason": "string summary",
  "recommendation": "PASS" | "REJECT"
}
"""


class AIEvaluator:
    """AI-Powered Technical Recruiter Evaluator engine."""

    def __init__(self, provider: str = "ollama"):
        self.provider = provider.lower()

    def evaluate_job(self, profile: dict, job: dict, threshold: float = 70.0) -> dict:
        """Evaluate job posting against candidate profile using LLM reasoning."""
        job_title = job.get("title", "Software / AI Engineer")
        company = job.get("company", "Target Company")
        description = job.get("description", "")
        apply_url = job.get("apply_url", job.get("url", ""))

        prompt_input = f"""
CANDIDATE PROFILE:
{json.dumps(profile, indent=2)}

JOB POSTING TO EVALUATE:
Title: {job_title}
Company: {company}
URL: {apply_url}
Description:
{description}
"""

        # Try LLM Provider with fallbacks
        try:
            res = self._execute_with_fallback(prompt_input)
            res["job_id"] = job.get("job_id", "job_101")
            res["title"] = job_title
            res["company"] = company
            res["apply_url"] = apply_url
            res["passed"] = res.get("score", 0) >= threshold
            return res

        except Exception as e:
            print(f"[AI EVALUATOR WARNING] LLM Evaluation failed ({e}). Falling back to heuristic recruiter evaluator.", file=sys.stderr)
            return self._fallback_evaluator(profile, job, threshold)

    def _execute_with_fallback(self, prompt: str) -> dict:
        """Attempt local Ollama first, then fall back to cloud providers."""
        order = []
        if self.provider:
            order.append(self.provider)

        for p in ["ollama", "groq", "cerebras", "openrouter"]:
            if p not in order:
                order.append(p)

        last_error = None
        for p in order:
            if self._is_on_cooldown(p):
                print(f"[AI] Skipping provider {p.upper()} (on 2-hour rate-limit/error cooldown)", file=sys.stderr)
                continue
            try:
                if p == "ollama":
                    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
                    return self._call_ollama(prompt, base_url, model)
                elif p == "groq":
                    api_key = os.getenv("GROQ_API_KEY")
                    if not api_key:
                        raise ValueError("GROQ_API_KEY not set")
                    return self._call_groq(prompt, api_key)
                elif p == "cerebras":
                    api_key = os.getenv("CEREBRAS_API_KEY")
                    if not api_key:
                        raise ValueError("CEREBRAS_API_KEY not set")
                    return self._call_cerebras(prompt, api_key)
                elif p == "openrouter":
                    api_key = os.getenv("OPENROUTER_API_KEY")
                    return self._call_openrouter(prompt, api_key)
            except Exception as e:
                print(f"[AI WARNING] Recruiter evaluator provider {p.upper()} failed: {e}", file=sys.stderr)
                self._set_cooldown(p)
                last_error = e

        raise RuntimeError(f"All Recruiter AI providers failed. Last error: {last_error}")

    def _is_on_cooldown(self, provider: str) -> bool:
        if provider == "ollama":
            return False
        cooldown_file = ".api_cooldowns.json"
        cooldown_duration = 7200  # 2 hours
        try:
            if os.path.exists(cooldown_file):
                with open(cooldown_file, "r") as f:
                    data = json.load(f)
                fail_time = data.get(provider, 0)
                if time.time() - fail_time < cooldown_duration:
                    return True
        except Exception:
            pass
        return False

    def _set_cooldown(self, provider: str):
        if provider == "ollama":
            return
        cooldown_file = ".api_cooldowns.json"
        try:
            data = {}
            if os.path.exists(cooldown_file):
                with open(cooldown_file, "r") as f:
                    data = json.load(f)
            data[provider] = time.time()
            with open(cooldown_file, "w") as f:
                json.dump(data, f)
            print(f"[AI COOLDOWN] Set 2-hour fallback cooldown for provider: {provider.upper()}", file=sys.stderr)
        except Exception:
            pass

    def _call_groq(self, prompt: str, api_key: str) -> dict:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": RECRUITER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            return json.loads(res.json()["choices"][0]["message"]["content"])
        raise RuntimeError(f"Groq API Error {res.status_code}: {res.text}")

    def _call_cerebras(self, prompt: str, api_key: str) -> dict:
        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3.1-8b",
            "messages": [
                {"role": "system", "content": RECRUITER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            return json.loads(res.json()["choices"][0]["message"]["content"])
        raise RuntimeError(f"Cerebras API Error {res.status_code}: {res.text}")

    def _call_openrouter(self, prompt: str, api_key: str) -> dict:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/llama-3-8b-instruct:free",
            "messages": [
                {"role": "system", "content": RECRUITER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return json.loads(res.json()["choices"][0]["message"]["content"])
        raise RuntimeError(f"OpenRouter API Error {res.status_code}: {res.text}")

    def _call_ollama(self, prompt: str, base_url: str, model: str) -> dict:
        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": RECRUITER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "stream": False,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            return json.loads(res.json()["choices"][0]["message"]["content"])
        raise RuntimeError(f"Ollama API Error {res.status_code}: {res.text}")

    def _fallback_evaluator(self, profile: dict, job: dict, threshold: float) -> dict:
        """Deterministic fallback evaluator if offline."""
        title = job.get("title", "").lower()
        desc = job.get("description", "").lower()
        full_text = f"{title} {desc}"

        core_skills = profile.get("core_skills", ["Python", "PyTorch", "FastAPI", "AWS"])
        matched = [s for s in core_skills if s.lower() in full_text]
        missing = [s for s in core_skills if s not in matched]

        score = min(100, int((len(matched) / max(len(core_skills), 1)) * 100 * 1.4))
        passed = score >= threshold

        return {
            "job_id": job.get("job_id", "job_101"),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "apply_url": job.get("apply_url", ""),
            "score": score,
            "passed": passed,
            "interviewProbability": "High" if score >= 80 else ("Medium" if score >= 70 else "Low"),
            "matchedRole": job.get("title", "AI Engineer"),
            "matchedSkills": matched,
            "missingSkills": missing,
            "strengths": ["Strong match on core skills", "Bosch Group AI internship background"],
            "weaknesses": ["Potential gap on specific framework requirements"],
            "reason": f"Fallback evaluation calculated {score}% skill overlap.",
            "recommendation": "PASS" if passed else "REJECT"
        }


def main():
    parser = argparse.ArgumentParser(description="Stage 2 AI Recruiter Job Evaluator CLI")
    parser.add_argument("--profile", default="source_profile.json", help="Path to source_profile.json")
    parser.add_argument("--job", default="samples/ai_engineer_job.json", help="Path to job JSON file or text")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "groq", "cerebras", "openrouter"], help="AI Provider")
    parser.add_argument("--threshold", type=float, default=70.0, help="Passing threshold score")
    args = parser.parse_args()

    # Load candidate profile
    with open(args.profile, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    # Load job description
    if args.job and os.path.exists(args.job):
        with open(args.job, "r", encoding="utf-8") as f:
            content = f.read()
            try:
                job_data = json.loads(content)
            except json.JSONDecodeError:
                job_data = {
                    "job_id": os.path.basename(args.job),
                    "title": os.path.basename(args.job),
                    "description": content,
                    "company": "Target Company"
                }
    else:
        stdin_content = sys.stdin.read()
        try:
            job_data = json.loads(stdin_content)
        except json.JSONDecodeError:
            job_data = {
                "job_id": "stdin_job",
                "title": "Ingested Job",
                "description": stdin_content,
                "company": "Target Company"
            }

    evaluator = AIEvaluator(provider=args.provider)
    result = evaluator.evaluate_job(profile_data, job_data, args.threshold)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
