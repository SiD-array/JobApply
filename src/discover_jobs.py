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
    args = parser.parse_args()

    engine = DiscoveryEngine()
    query = SearchQuery(
        keywords=args.keywords,
        location=args.location,
        limit_per_provider=args.limit
    )

    jobs: List[Job] = engine.discover_jobs(query, active_providers=args.providers)

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
