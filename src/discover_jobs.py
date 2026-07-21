#!/usr/bin/env python3
"""
Stage 1: Job Discovery & Ingestion Script
Fetches live job postings (AI/ML, Python Engineer, Software Engineer)
and sends them to n8n Webhook (or local pipeline) for evaluation & application.
"""

import sys
import os
import json
import time
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

# Free tech job feeds & Greenhouse/Lever company endpoints
DEFAULT_FEEDS = [
    "https://remoteok.com/api?tag=python",
    "https://remoteok.com/api?tag=ai",
    "https://remoteok.com/api?tag=machine-learning"
]


def fetch_remoteok_jobs(limit: int = 10) -> list:
    """Fetch live jobs from RemoteOK API."""
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get("https://remoteok.com/api?tag=python", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # First item is disclaimer, skip it
            for item in data[1:limit+1]:
                if isinstance(item, dict) and "position" in item:
                    jobs.append({
                        "job_id": f"remoteok_{item.get('id', int(time.time()))}",
                        "title": item.get("position", "Software Engineer"),
                        "company": item.get("company", "Remote Company"),
                        "description": item.get("description", item.get("position", "")),
                        "apply_url": item.get("url", "https://remoteok.com")
                    })
    except Exception as e:
        print(f"[DISCOVERY WARNING] RemoteOK fetch error: {e}", file=sys.stderr)
    return jobs


def send_to_n8n_webhook(job: dict, webhook_url: str) -> bool:
    """Post job payload to n8n Webhook trigger."""
    try:
        res = requests.post(webhook_url, json=job, timeout=10)
        if res.status_code in (200, 201):
            print(f"[INGESTED] {job['title']} @ {job['company']} -> n8n Webhook OK")
            return True
        else:
            print(f"[INGEST FAILED] {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"[INGEST ERROR] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Stage 1 Live Job Discovery & Ingestion")
    parser.add_argument("--webhook", default="http://localhost:5678/webhook/job-ingest", help="n8n Webhook URL")
    parser.add_argument("--limit", type=int, default=5, help="Number of jobs to discover")
    parser.add_argument("--direct", action="store_true", help="Run local pipeline directly instead of posting to n8n")
    args = parser.parse_args()

    print(f"🔍 [DISCOVERY] Searching for live AI/ML & Software Engineer job postings...")
    jobs = fetch_remoteok_jobs(limit=args.limit)

    if not jobs:
        print("⚠️ No live jobs fetched. Using sample AI Engineer job.")
        jobs = [{
            "job_id": "ai_job_2026",
            "title": "AI Engineer / Machine Learning Developer",
            "company": "NextGen AI Labs",
            "description": "Seeking an AI Engineer to design machine learning pipelines, multi-agent LLM systems, and cloud-native services.",
            "apply_url": "https://company.greenhouse.io/job/ai_job_2026"
        }]

    print(f"✅ Found {len(jobs)} live job postings!\n")

    for idx, job in enumerate(jobs, 1):
        print(f"[{idx}/{len(jobs)}] {job['title']} @ {job['company']}")
        if args.direct:
            # Trigger local pipeline directly
            cmd = [sys.executable, "run_pipeline.py", "--url", job["apply_url"], "--title", job["title"], "--company", job["company"]]
            subprocess.run(cmd)
        else:
            # Post to n8n webhook
            send_to_n8n_webhook(job, args.webhook)
        time.sleep(1)


if __name__ == "__main__":
    main()
