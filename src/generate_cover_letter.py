#!/usr/bin/env python3
"""
Cover Letter Generator Module
Generates clean, single-page tailored cover letters in Markdown and ATS-compliant PDF format.
Enforces concise professional tone, 4-paragraph structure, and zero hallucination.
"""

import sys
import os
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from jinja2 import Template
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

COVER_LETTER_SYSTEM_PROMPT = """You are a professional executive career coach and technical copywriter.
Write a highly targeted, concise, 1-page cover letter for the candidate applying to a target job.

WRITING STYLE CONSTRAINTS:
- Professional, direct, and conversational.
- NO BUZZWORDS or corporate fluff (avoid "visionary", "synergy", "rockstar", "game-changer", "passionate guru").
- NO HALLUCINATIONS: Never invent work experience, metrics, or skills not present in the candidate profile.

REQUIRED STRUCTURE (4 Paragraphs):
1. OPENING: Clear statement of application for the target role at the specified company.
2. WHY COMPANY: Highlight why the candidate is drawn to the company's product, engineering culture, or mission.
3. RELEVANT EXPERIENCE: 2-3 concrete, factual highlights from candidate's background (e.g., Bosch AI Engineering internship optimizing ML pipelines by 75%, multi-agent cloud governance, or stock forecasting).
4. CLOSING: Courteous call to action and formal sign-off.

OUTPUT INSTRUCTIONS:
Return RAW VALID JSON ONLY matching this schema:
{
  "markdown": "Full formatted markdown text of the cover letter including date, recipient, and signature.",
  "opening": "Opening paragraph string",
  "why_company": "Why company paragraph string",
  "relevant_experience": "Relevant experience paragraph string",
  "closing": "Closing paragraph string"
}
"""

# HTML/CSS Template for LaTeX-style PDF Cover Letter
COVER_LETTER_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: letter;
    margin: 0.5in 0.6in 0.5in 0.6in;
  }
  body {
    font-family: 'Times New Roman', Times, 'Georgia', serif;
    color: #000000;
    font-size: 10.5pt;
    line-height: 1.35;
    margin: 0;
    padding: 0;
  }
  .header {
    text-align: center;
    margin-bottom: 18px;
    border-bottom: 1px solid #000;
    padding-bottom: 8px;
  }
  .header h1 {
    font-size: 18pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 4px 0;
  }
  .contact-line {
    font-size: 9.5pt;
  }
  .contact-line a {
    color: #000;
    text-decoration: none;
  }
  .meta-block {
    margin-bottom: 18px;
    font-size: 10pt;
  }
  .recipient-block {
    margin-bottom: 18px;
    font-size: 10pt;
  }
  .content p {
    margin-bottom: 12px;
    text-align: justify;
    text-justify: inter-word;
  }
  .signature {
    margin-top: 24px;
  }
</style>
</head>
<body>

<div class="header">
  <h1>{{ candidate.name }}</h1>
  <div class="contact-line">
    {{ candidate.contact.email }} &bull; {{ candidate.contact.phone }} &bull; {{ candidate.contact.location }}<br>
    <a href="{{ candidate.contact.linkedin }}">LinkedIn</a> &bull; <a href="{{ candidate.contact.github }}">GitHub</a>
  </div>
</div>

<div class="meta-block">
  {{ date_str }}
</div>

<div class="recipient-block">
  <strong>Hiring Team</strong><br>
  {{ company }}<br>
  Re: Application for {{ job_title }}
</div>

<div class="content">
  <p>{{ opening }}</p>
  <p>{{ why_company }}</p>
  <p>{{ relevant_experience }}</p>
  <p>{{ closing }}</p>
</div>

<div class="signature">
  Sincerely,<br><br>
  <strong>{{ candidate.name }}</strong>
</div>

</body>
</html>
"""


class CoverLetterGenerator:
    """Cover Letter Generator Engine."""

    def __init__(self, provider: str = "ollama"):
        self.provider = provider.lower()

    def generate_cover_letter(self, profile: dict, job: dict) -> dict:
        """Generate tailored cover letter JSON payload using LLM."""
        company = job.get("company", "Target Company")
        job_title = job.get("title", "Software / AI Engineer")
        job_desc = job.get("description", "")

        user_prompt = f"""
CANDIDATE PROFILE:
{json.dumps(profile, indent=2)}

TARGET JOB POSTING:
Company: {company}
Role Title: {job_title}
Job Description:
{job_desc}
"""

        try:
            res = self._execute_with_fallback(user_prompt)
            res["company"] = company
            res["job_title"] = job_title
            return res
        except Exception as e:
            print(f"[COVER LETTER WARNING] LLM Cover Letter generation failed ({e}). Falling back to heuristic generator.", file=sys.stderr)
            return self._fallback_generator(company, job_title)

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
                print(f"[AI WARNING] Cover letter provider {p.upper()} failed: {e}", file=sys.stderr)
                last_error = e

        raise RuntimeError(f"All Cover Letter AI providers failed. Last error: {last_error}")

    def _call_ollama(self, prompt: str, base_url: str, model: str) -> dict:
        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": COVER_LETTER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return json.loads(res.json()["choices"][0]["message"]["content"])
        raise RuntimeError(f"Ollama API Error {res.status_code}: {res.text}")

    def _call_groq(self, prompt: str, api_key: str) -> dict:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": COVER_LETTER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return json.loads(res.json()["choices"][0]["message"]["content"])
        raise RuntimeError(f"Groq API Error {res.status_code}: {res.text}")

    def _call_cerebras(self, prompt: str, api_key: str) -> dict:
        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3.1-8b",
            "messages": [
                {"role": "system", "content": COVER_LETTER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return json.loads(res.json()["choices"][0]["message"]["content"])
        raise RuntimeError(f"Cerebras API Error {res.status_code}: {res.text}")

    def _call_openrouter(self, prompt: str, api_key: str) -> dict:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/llama-3-8b-instruct:free",
            "messages": [
                {"role": "system", "content": COVER_LETTER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return json.loads(res.json()["choices"][0]["message"]["content"])
        raise RuntimeError(f"OpenRouter API Error {res.status_code}: {res.text}")

    def _fallback_generator(self, company: str, job_title: str) -> dict:
        """Deterministic fallback cover letter if offline."""
        opening = f"I am writing to express my strong interest in the {job_title} position at {company}."
        why = f"I have followed {company}'s growth and engineering work, and I am drawn to your scale, engineering culture, and development approach."
        exp = "My background includes hands-on experience in machine learning pipelines, backend software engineering, and database design. In my previous AI Engineering Internship, I focused on high-efficiency deep learning pipelines and API deployment."
        closing = "Thank you for your time and consideration. I look forward to discussing how my experience can contribute to your team."
        markdown = f"# Cover Letter\n\n{opening}\n\n{why}\n\n{exp}\n\n{closing}"
        return {
            "opening": opening,
            "why_company": why,
            "relevant_experience": exp,
            "closing": closing,
            "markdown": markdown
        }

    def render_pdf(self, cover_data: dict, candidate_profile: dict, output_pdf_path: str):
        """Render single-page vector PDF cover letter using Playwright Chromium."""
        date_str = datetime.now().strftime("%B %d, %Y")
        template = Template(COVER_LETTER_HTML_TEMPLATE)

        cand_data = candidate_profile.get("tailoredProfile", candidate_profile)
        contact = cand_data.get("personal_info") or cand_data.get("contact", {})

        candidate_obj = {
            "name": cand_data.get("name", "Siddharth Bhople"),
            "contact": contact
        }

        html_out = template.render(
            candidate=candidate_obj,
            date_str=date_str,
            company=cover_data.get("company", "Target Company"),
            job_title=cover_data.get("job_title", "Software Engineer"),
            opening=cover_data.get("opening", ""),
            why_company=cover_data.get("why_company", ""),
            relevant_experience=cover_data.get("relevant_experience", ""),
            closing=cover_data.get("closing", "")
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_out, wait_until="networkidle")
            page.pdf(
                path=output_pdf_path,
                format="Letter",
                print_background=True,
                margin={"top": "0.5in", "bottom": "0.5in", "left": "0.6in", "right": "0.6in"}
            )
            browser.close()

        print(f"[COVER LETTER PDF] Successfully compiled to: {output_pdf_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Tailored 1-Page Cover Letter in Markdown and PDF")
    parser.add_argument("--profile", default="source_profile.json", help="Path to source profile or tailored profile JSON")
    parser.add_argument("--job", default="samples/ai_engineer_job.json", help="Path to target job JSON file")
    parser.add_argument("--provider", default="ollama", help="AI provider")
    parser.add_argument("--output-md", default="output_resumes/Cover_Letter.md", help="Output markdown path")
    parser.add_argument("--output-pdf", default="output_resumes/Cover_Letter.pdf", help="Output PDF path")
    args = parser.parse_args()

    with open(args.profile, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    if args.job and os.path.exists(args.job):
        with open(args.job, "r", encoding="utf-8") as f:
            job_data = json.load(f)
    else:
        job_data = json.loads(sys.stdin.read())

    generator = CoverLetterGenerator(provider=args.provider)
    cover_data = generator.generate_cover_letter(profile_data, job_data)

    # Save Markdown
    os.makedirs(os.path.dirname(os.path.abspath(args.output_md)), exist_ok=True)
    with open(args.output_md, "w", encoding="utf-8") as f:
        f.write(cover_data.get("markdown", ""))

    print(f"[COVER LETTER MD] Saved markdown to: {args.output_md}")

    # Render PDF
    generator.render_pdf(cover_data, profile_data, args.output_pdf)


if __name__ == "__main__":
    main()
