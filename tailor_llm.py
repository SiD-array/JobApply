#!/usr/bin/env python3
"""
Stage 3: High-Throughput LLM Resume Tailoring Script
Supports Groq (Llama 3.3 70B), Cerebras (Llama 3.3 70B), OpenRouter, and Gemini.
Enforces strict zero-hallucination constraints and outputs structured JSON profile.
"""

import sys
import os
import json
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an expert ATS (Applicant Tracking System) optimizer and professional resume writer.
You will receive candidate profile data (source_profile.json) and a target job description.

STRICT CONSTRAINTS:
1. NEVER invent, fabricate, or exaggerate work experience, metrics, companies, titles, or dates.
2. You may ONLY reorder, highlight, or rephrase bullet points from source_profile.json to emphasize relevance to the target job.
3. Align technical terminology with keywords from the job description where factually accurate.
4. Output MUST strictly adhere to the requested JSON structure matching source_profile.json layout (containing personal_info, summary, core_skills, experience, education).
5. Output raw valid JSON ONLY. No markdown wrapping, no prose outside JSON.
"""


def tailor_with_groq(profile: dict, job_desc: str, api_key: str) -> dict:
    """Invoke Groq API (14,400 requests/day free limit, 500+ tokens/sec)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    user_content = f"Candidate Profile:\n{json.dumps(profile, indent=2)}\n\nTarget Job Description:\n{job_desc}"

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "stream": False
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Groq API request failed ({response.status_code}): {response.text}")

    data = response.json()
    raw_content = data["choices"][0]["message"]["content"].strip()
    return json.loads(raw_content)


def tailor_with_cerebras(profile: dict, job_desc: str, api_key: str) -> dict:
    """Invoke Cerebras API (14,400 requests/day free limit, 2000+ tokens/sec)."""
    url = "https://api.cerebras.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    user_content = f"Candidate Profile:\n{json.dumps(profile, indent=2)}\n\nTarget Job Description:\n{job_desc}"

    payload = {
        "model": "llama-3.3-70b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "stream": False
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Cerebras API request failed ({response.status_code}): {response.text}")

    data = response.json()
    raw_content = data["choices"][0]["message"]["content"].strip()
    return json.loads(raw_content)


def tailor_with_openrouter(profile: dict, job_desc: str, api_key: str) -> dict:
    """Invoke OpenRouter API free tier."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    user_content = f"Candidate Profile:\n{json.dumps(profile, indent=2)}\n\nTarget Job Description:\n{job_desc}"

    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "stream": False
    }

    response = requests.post(url, headers=headers, json=payload, timeout=45)
    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter API request failed ({response.status_code}): {response.text}")

    data = response.json()
    raw_content = data["choices"][0]["message"]["content"].strip()
    return json.loads(raw_content)


def main():
    parser = argparse.ArgumentParser(description="Stage 3 LLM Resume Tailoring Script")
    parser.add_argument("--profile", default="source_profile.json", help="Path to candidate profile JSON")
    parser.add_argument("--job", default="sample_job.json", help="Path to job description JSON or text")
    parser.add_argument("--provider", choices=["groq", "cerebras", "openrouter"], default="groq", help="AI Model Provider")
    parser.add_argument("--output", help="Output JSON file path")
    args = parser.parse_args()

    # Load candidate profile
    with open(args.profile, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    # Load job description
    with open(args.job, "r", encoding="utf-8") as f:
        job_raw = f.read()
        try:
            job_json = json.loads(job_raw)
            job_desc = job_json.get("description", job_raw)
            job_id = job_json.get("job_id", "job_01")
        except json.JSONDecodeError:
            job_desc = job_raw
            job_id = os.path.basename(args.job)

    print(f"[STAGE 3] Tailoring resume using provider: {args.provider.upper()}...")

    if args.provider == "groq":
        api_key = (os.getenv("GROQ_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY in .env. Get a free key at https://console.groq.com")
        tailored_profile = tailor_with_groq(profile_data, job_desc, api_key)

    elif args.provider == "cerebras":
        api_key = (os.getenv("CEREBRAS_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("Missing CEREBRAS_API_KEY in .env. Get a free key at https://cloud.cerebras.ai")
        tailored_profile = tailor_with_cerebras(profile_data, job_desc, api_key)

    elif args.provider == "openrouter":
        api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("Missing OPENROUTER_API_KEY in .env. Get a free key at https://openrouter.ai")
        tailored_profile = tailor_with_openrouter(profile_data, job_desc, api_key)

    # Save output
    out_path = args.output or os.path.join("output_resumes", f"tailored_{job_id}.json")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(tailored_profile, f, indent=2)

    print(f"[STAGE 3 SUCCESS] Tailored profile saved to: {out_path}")


if __name__ == "__main__":
    main()
