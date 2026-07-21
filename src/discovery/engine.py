"""
Configurable Job Discovery Engine.
Orchestrates job discovery across registered providers (LinkedIn, WellFound, Greenhouse, Lever, Ashby, Workday),
deduplicates results, and normalizes output into the shared Job model.
"""

import sys
import os
import json
import requests
from typing import List, Dict, Type
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.discovery.models import Job, SearchQuery
from src.discovery.base_provider import BaseJobProvider
from src.discovery.providers import (
    LinkedInProvider,
    WellFoundProvider,
    GreenhouseProvider,
    LeverProvider,
    AshbyProvider,
    WorkdayProvider
)


class DiscoveryEngine:
    """Engine for orchestrating multi-provider job discovery."""

    def __init__(self):
        self.providers: Dict[str, BaseJobProvider] = {}
        # Register default 6 providers
        self.register_provider(LinkedInProvider())
        self.register_provider(WellFoundProvider())
        self.register_provider(GreenhouseProvider())
        self.register_provider(LeverProvider())
        self.register_provider(AshbyProvider())
        self.register_provider(WorkdayProvider())

    def register_provider(self, provider: BaseJobProvider):
        """Register a new job board provider implementing BaseJobProvider."""
        self.providers[provider.name.lower()] = provider
        print(f"[ENGINE] Registered provider: {provider.name}")

    def discover_jobs(self, query: SearchQuery, active_providers: List[str] = None) -> List[Job]:
        """
        Run discovery across registered providers concurrently.
        Deduplicates jobs by URL and title/company combination.
        """
        target_providers = []
        if active_providers:
            for p_name in active_providers:
                p_lower = p_name.lower()
                if p_lower in self.providers:
                    target_providers.append(self.providers[p_lower])
        else:
            target_providers = list(self.providers.values())

        all_jobs: List[Job] = []
        seen_urls = set()
        seen_keys = set()

        print(f"\n[DISCOVERY ENGINE] Searching across {len(target_providers)} providers...")
        print(f"   Keywords: {query.keywords} | Location: {query.location}\n")

        with ThreadPoolExecutor(max_workers=len(target_providers)) as executor:
            future_to_provider = {
                executor.submit(provider.fetch_jobs, query): provider
                for provider in target_providers
            }

            for future in as_completed(future_to_provider):
                provider = future_to_provider[future]
                try:
                    jobs = future.result()
                    count = 0
                    for job in jobs:
                        # Age Filter
                        if query.max_age_hours:
                            try:
                                post_dt = datetime.strptime(job.postedDate, "%Y-%m-%d")
                                delta_days = (datetime.now() - post_dt).days
                                if delta_days * 24 > query.max_age_hours:
                                    continue
                            except Exception:
                                pass

                        key = f"{job.title.lower()}_{job.company.lower()}"
                        if job.url not in seen_urls and key not in seen_keys:
                            seen_urls.add(job.url)
                            seen_keys.add(key)
                            all_jobs.append(job)
                            count += 1
                    print(f"  + {provider.name}: Found {count} unique jobs")
                except Exception as e:
                    print(f"  x {provider.name} failed: {e}", file=sys.stderr)

        print(f"\n[DISCOVERY COMPLETE] Total normalized unique jobs: {len(all_jobs)}")
        return all_jobs

    def send_to_n8n(self, jobs: List[Job], webhook_url: str) -> int:
        """Send discovered Job models to n8n Webhook."""
        success_count = 0
        for job in jobs:
            try:
                res = requests.post(webhook_url, json=job.to_dict(), timeout=5)
                if res.status_code in (200, 201):
                    success_count += 1
            except Exception:
                pass
        print(f"[N8N INGEST] Sent {success_count}/{len(jobs)} jobs to n8n Webhook.")
        return success_count
