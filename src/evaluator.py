#!/usr/bin/env python3
"""
Stage 2: Evaluation Gate Script
Extracts skill keywords and requirements from a job description and computes
an overlap score against candidate source profile skills and experience.
Outputs JSON to stdout for easy n8n processing.
"""

import sys
import os
import json
import re
import argparse
from typing import Dict, Any, List, Set

DEFAULT_THRESHOLD = 70.0


def extract_keywords(text: str) -> Set[str]:
    """Clean and extract keywords from text string."""
    text_clean = re.sub(r'[^a-zA-Z0-9\s\+\#\.]', ' ', text)
    tokens = [t.strip().lower() for t in text_clean.split() if len(t.strip()) > 1]
    
    # Common tech term normalization
    normalized = set()
    for t in tokens:
        if t in ['py', 'python3']:
            normalized.add('python')
        elif t in ['postgres', 'postgresql']:
            normalized.add('postgresql')
        elif t in ['rest', 'restful', 'apis', 'api']:
            normalized.add('rest apis')
        elif t in ['cicd', 'ci/cd']:
            normalized.add('ci/cd')
        elif t in ['llm', 'llms', 'gpt', 'ai']:
            normalized.add('llm integration')
        else:
            normalized.add(t)
    return normalized


def evaluate_job_fit(profile: Dict[str, Any], job: Dict[str, Any], threshold: float = DEFAULT_THRESHOLD) -> Dict[str, Any]:
    """Calculate match score between candidate profile and job description."""
    core_skills = [s.strip() for s in profile.get("core_skills", [])]
    core_skills_lower = [s.lower() for s in core_skills]
    
    # Collect all tokens from candidate profile
    exp_text = " ".join([
        f"{exp.get('title', '')} {exp.get('company', '')} " + " ".join(exp.get("bullet_points", []))
        for exp in profile.get("experience", [])
    ])
    summary_text = profile.get("summary", "")
    full_profile_text = f"{' '.join(core_skills)} {summary_text} {exp_text}".lower()
    profile_keywords = extract_keywords(full_profile_text)

    job_title = job.get("title", "")
    job_desc = job.get("description", "")
    job_text = f"{job_title} {job_desc}".lower()
    job_keywords = extract_keywords(job_text)

    # 1. Candidate Core Skill Match in JD
    matched_skills = []
    missing_skills = []
    for skill in core_skills:
        skill_lower = skill.lower()
        if skill_lower in job_text or any(k in job_keywords for k in extract_keywords(skill_lower)):
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)

    # 2. Extract key domain/technical terms from JD
    common_tech_terms = [
        'python', 'javascript', 'typescript', 'react', 'node.js', 'express', 'fastapi',
        'django', 'flask', 'postgresql', 'mysql', 'mongodb', 'redis', 'aws', 'gcp',
        'azure', 'docker', 'kubernetes', 'ci/cd', 'git', 'rest apis', 'graphql',
        'llm integration', 'playwright', 'selenium', 'agile', 'scrum', 'microservices'
    ]
    jd_tech_requirements = [term for term in common_tech_terms if term in job_text or term in job_keywords]

    # Calculate match ratio
    if jd_tech_requirements:
        matched_jd_terms = [term for term in jd_tech_requirements if term in profile_keywords or term in full_profile_text]
        score_jd = (len(matched_jd_terms) / len(jd_tech_requirements)) * 100.0
    else:
        score_jd = 100.0 if matched_skills else 0.0

    skill_coverage = (len(matched_skills) / len(core_skills) * 100.0) if core_skills else 0.0
    
    # Final composite score biased towards matching what the JD actually asks for
    score = round(0.65 * score_jd + 0.35 * skill_coverage, 2) if jd_tech_requirements else round(skill_coverage, 2)
    score = min(score, 100.0)

    passed = score >= threshold
    reason = (
        f"Score {score}% meets threshold of {threshold}%"
        if passed
        else f"Score {score}% is below required threshold of {threshold}%"
    )

    return {
        "job_id": job.get("job_id", "unknown"),
        "title": job_title,
        "company": job.get("company", ""),
        "apply_url": job.get("apply_url", ""),
        "score": score,
        "passed": passed,
        "threshold": threshold,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "reason": reason
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate job description fit against candidate profile.")
    parser.add_argument("--profile", default="source_profile.json", help="Path to source_profile.json")
    parser.add_argument("--job", help="Path to job JSON file")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="Passing threshold score percentage")
    args = parser.parse_args()

    # Load profile
    with open(args.profile, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    # Load job description from file or standard input
    if args.job:
        with open(args.job, "r", encoding="utf-8") as f:
            content = f.read()
            try:
                job_data = json.loads(content)
            except json.JSONDecodeError:
                # If file is text/markdown instead of JSON, construct job dict from raw text
                job_data = {
                    "job_id": os.path.basename(args.job),
                    "title": os.path.basename(args.job),
                    "description": content,
                    "company": "Unknown"
                }
    else:
        # Read from stdin if no job file provided
        stdin_content = sys.stdin.read()
        try:
            job_data = json.loads(stdin_content)
        except json.JSONDecodeError:
            job_data = {
                "job_id": "stdin_job",
                "title": "Ingested Job",
                "description": stdin_content,
                "company": "Unknown"
            }

    result = evaluate_job_fit(profile_data, job_data, args.threshold)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
