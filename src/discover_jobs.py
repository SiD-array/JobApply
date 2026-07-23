#!/usr/bin/env python3
"""
Stage 1: Job Discovery & Ingestion CLI
Uses the configurable DiscoveryEngine to search across LinkedIn, WellFound,
Greenhouse, Lever, Ashby, and Workday providers.
Outputs normalized Job models and feeds them to n8n Webhook or local storage.
"""

import sys
import os
import json
import argparse
from typing import List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from src.discovery.models import SearchQuery, Job
from src.discovery.engine import DiscoveryEngine


def main():
    parser = argparse.ArgumentParser(description="Multi-Provider Configurable Job Discovery Engine CLI")
    parser.add_argument("--keywords", nargs="+", default=["AI Engineer", "Machine Learning", "Software Engineer"], help="Search keywords")
    parser.add_argument("--location", default="United States", help="Search location")
    parser.add_argument("--providers", nargs="+", choices=["linkedin", "wellfound", "greenhouse", "lever", "ashby", "workday"], help="Filter specific providers")
    parser.add_argument("--limit", type=int, default=5, help="Limit per provider")
    parser.add_argument("--webhook", default="http://localhost:5678/webhook/job-ingest", help="n8n Webhook URL")
    parser.add_argument("--output", default="samples/discovered_jobs.json", help="Save output JSON path")
    parser.add_argument("--max-age-hours", type=int, help="Filter jobs posted within last X hours")
    parser.add_argument("--target-passed", type=int, default=0, help="Loop/search until finding at least X jobs passing evaluation")
    parser.add_argument("--profile", default="source_profile.json", help="Path to source candidate profile JSON")
    args = parser.parse_args()

    engine = DiscoveryEngine()
    
    # If target-passed is specified, we evaluate discovered jobs locally to filter out poor matches
    profile_data = {}
    if args.target_passed > 0:
        from src.evaluator import AIEvaluator
        evaluator = AIEvaluator(provider="groq")
        with open(args.profile, "r", encoding="utf-8") as f:
            profile_data = json.load(f)

    # Initial query limits
    limit = args.limit
    passed_jobs: List[Job] = []
    attempts = 0

    while attempts < 3:
        query = SearchQuery(
            keywords=args.keywords,
            location=args.location,
            limit_per_provider=limit,
            max_age_hours=args.max_age_hours
        )
        discovered = engine.discover_jobs(query, active_providers=args.providers)
        
        if args.target_passed > 0:
            print(f"\n[AI GATE] Evaluating {len(discovered)} discovered jobs to find {args.target_passed} matches...")
            passed_jobs = []
            for j in discovered:
                # Convert Job object to dict
                j_dict = j.to_dict()
                res = evaluator.evaluate_job(profile_data, j_dict, threshold=70.0)
                if res.get("passed"):
                    j.score = res.get("score")
                    j.passed = res.get("passed")
                    j.matched_skills = res.get("matchedSkills") or res.get("matched_skills") or []
                    j.missing_skills = res.get("missingSkills") or res.get("missing_skills") or []
                    passed_jobs.append(j)
                    print(f"  + Match PASSED ({res.get('score')}%): {j.title} @ {j.company}")
                if len(passed_jobs) >= args.target_passed:
                    break
            
            print(f"[AI GATE] Found {len(passed_jobs)}/ {args.target_passed} passing jobs.")
            if len(passed_jobs) >= args.target_passed:
                jobs = passed_jobs
                break
            else:
                # Double search limits and try again
                limit *= 2
                attempts += 1
                print(f"[WARNING] Did not reach target of {args.target_passed} passed jobs. Increasing batch size to {limit} per provider...")
        else:
            jobs = discovered
            break

    # Convert to JSON dicts
    jobs_dict = [j.to_dict() for j in jobs]

    # Save output
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(jobs_dict, f, indent=2)

    print(f"\n[SAVED] Saved {len(jobs)} normalized jobs to: {args.output}")

    # Optionally post to n8n
    if args.webhook:
        engine.send_to_n8n(jobs, args.webhook)


if __name__ == "__main__":
    main()
