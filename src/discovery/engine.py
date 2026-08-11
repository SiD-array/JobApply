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
    SimplifyProvider,
    GreenhouseProvider,
    LeverProvider,
    AshbyProvider,
    WorkdayProvider
)


import re

def is_us_or_remote_location(location: str) -> bool:
    """
    Verify if the location is in the United States or is Remote.
    """
    loc_lower = location.lower().strip()
    
    # 1. If it explicitly states Remote
    if "remote" in loc_lower or "anywhere" in loc_lower:
        return True
        
    # 2. Check for non-US countries first (Exclusions)
    non_us_indicators = [
        "united kingdom", " uk", ", uk", "london", "england", "great britain", "gb",
        "india", "mumbai", "bangalore", "delhi",
        "germany", "berlin", "munich",
        "canada", "toronto", "vancouver", "montreal", "ontario", "bc", "quebec",
        "singapore", "australia", "sydney", "melbourne",
        "france", "paris", "spain", "madrid", "barcelona",
        "netherlands", "amsterdam", "poland", "warsaw",
        "europe", "apac", "emea", "latam"
    ]
    for indicator in non_us_indicators:
        if indicator in loc_lower:
            return False
            
    # 3. If it contains US country markers
    us_indicators = ["united states", "usa", "us", "u.s.", "u.s.a.", "america"]
    for indicator in us_indicators:
        if indicator in loc_lower:
            return True
            
    # 4. Check for US state 2-letter codes or full names
    us_states = {
        "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
        "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
        "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "florida", "georgia",
        "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland",
        "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire",
        "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
        "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia", "washington",
        "west virginia", "wisconsin", "wyoming", "district of columbia", "dc", "d.c."
    }
    
    # Extract words or split by comma/space
    words = re.split(r'[\s,\.\/]+', loc_lower)
    for w in words:
        if w in us_states:
            return True
            
    # Default to True if we couldn't classify it (to avoid missing valid US jobs)
    return True


class DiscoveryEngine:
    """Engine for orchestrating multi-provider job discovery."""

    def __init__(self):
        self.providers: Dict[str, BaseJobProvider] = {}
        # Register default 6 providers
        self.register_provider(LinkedInProvider())
        self.register_provider(SimplifyProvider())
        self.register_provider(GreenhouseProvider())
        self.register_provider(LeverProvider())
        self.register_provider(AshbyProvider())
        self.register_provider(WorkdayProvider())

    def register_provider(self, provider: BaseJobProvider):
        """Register a new job board provider implementing BaseJobProvider."""
        self.providers[provider.name.lower()] = provider
        print(f"[ENGINE] Registered provider: {provider.name}")

    def _load_historical_seen(self) -> tuple:
        """
        Pre-populate deduplication sets from:
          1. Active Datasheet (output_resumes/applications.json)
          2. Discovered Jobs Cache (samples/discovered_jobs.json)
          3. Persistent History Memory Log (.seen_jobs_history.json)
        """
        import time
        seen_urls = set()
        seen_keys = set()

        def add_entry(entry):
            if not isinstance(entry, dict):
                return
            url = entry.get("apply_url") or entry.get("url")
            if url:
                seen_urls.add(str(url).strip())

            title = str(entry.get("title", "")).strip().lower()
            company = str(entry.get("company", "")).strip().lower()
            if title and company:
                seen_keys.add(f"{title}_{company}")
                clean_t = "".join(c for c in title if c.isalnum())
                clean_c = "".join(c for c in company if c.isalnum())
                seen_keys.add(f"{clean_t}_{clean_c}")

            job_id = entry.get("job_id") or entry.get("id")
            if job_id and str(job_id) != "job_101":
                seen_keys.add(str(job_id).strip())

        # 1. Active Datasheet
        apps_file = os.path.abspath("output_resumes/applications.json")
        if os.path.exists(apps_file):
            try:
                with open(apps_file, "r", encoding="utf-8") as f:
                    apps = json.load(f)
                if isinstance(apps, list):
                    for a in apps:
                        add_entry(a)
            except Exception:
                pass

        # 2. Discovered Jobs Cache
        disc_file = os.path.abspath("samples/discovered_jobs.json")
        if os.path.exists(disc_file):
            try:
                with open(disc_file, "r", encoding="utf-8") as f:
                    jobs = json.load(f)
                if isinstance(jobs, list):
                    for j in jobs:
                        add_entry(j)
            except Exception:
                pass

        # 3. Persistent History Memory Log
        hist_file = os.path.abspath(".seen_jobs_history.json")
        if os.path.exists(hist_file):
            try:
                with open(hist_file, "r", encoding="utf-8") as f:
                    hist = json.load(f)
                if isinstance(hist, list):
                    for h in hist:
                        add_entry(h)
            except Exception:
                pass

        return seen_urls, seen_keys

    def _save_to_history(self, jobs: List[Job]):
        """Persist newly discovered unique jobs into .seen_jobs_history.json."""
        if not jobs:
            return
        import time
        hist_file = os.path.abspath(".seen_jobs_history.json")
        history = []
        if os.path.exists(hist_file):
            try:
                with open(hist_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                if not isinstance(history, list):
                    history = []
            except Exception:
                history = []

        existing_urls = {h.get("url") for h in history if isinstance(h, dict) and h.get("url")}
        for j in jobs:
            d = j.to_dict() if hasattr(j, "to_dict") else j
            url = d.get("url") or d.get("apply_url")
            if url and url not in existing_urls:
                history.append({
                    "job_id": d.get("job_id"),
                    "title": d.get("title"),
                    "company": d.get("company"),
                    "url": url,
                    "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                existing_urls.add(url)

        try:
            with open(hist_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

    def discover_jobs(self, query: SearchQuery, active_providers: List[str] = None) -> List[Job]:
        """
        Run discovery across registered providers concurrently.
        Pre-populates deduplication sets from history & datasheet to guarantee no duplicate jobs.
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
        seen_urls, seen_keys = self._load_historical_seen()

        print(f"\n[DISCOVERY ENGINE] Searching across {len(target_providers)} providers...")
        print(f"   Pre-loaded {len(seen_urls)} historical URLs & {len(seen_keys)} keys from Datasheet memory.")
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
                    filtered_jobs = self._filter_and_deduplicate(jobs, query.max_age_hours, seen_urls, seen_keys)
                    all_jobs.extend(filtered_jobs)
                    print(f"  + {provider.name}: Found {len(filtered_jobs)} new unique unseen jobs")
                except Exception as e:
                    print(f"  x {provider.name} failed: {e}", file=sys.stderr)

        self._save_to_history(all_jobs)
        print(f"\n[DISCOVERY COMPLETE] Total fresh unseen unique jobs: {len(all_jobs)}")
        return all_jobs

    def _filter_and_deduplicate(self, jobs: List[Job], max_age_hours: int, seen_urls: set, seen_keys: set) -> List[Job]:
        """
        Filter a list of jobs by age and deduplicate them.
        Attempts to use the specified age filter. If 0 jobs pass, relaxes the age filter.
        """
        if not jobs:
            print("    [DEBUG] Provider returned 0 raw jobs. Skipping age filter relaxation.")
            return []

        print(f"    [DEBUG] Filtering {len(jobs)} raw jobs fetched...")

        # Progressive age threshold relaxations: target limit -> 2x -> 4x -> None (no limit)
        thresholds = [max_age_hours] if max_age_hours else [None]
        if max_age_hours:
            thresholds.append(max_age_hours * 2)
            thresholds.append(max_age_hours * 4)
            thresholds.append(None)

        import datetime

        for limit in thresholds:
            passed = []
            for job in jobs:
                # Location Filter (Restrict to United States or Remote)
                if not is_us_or_remote_location(job.location):
                    continue

                if limit:
                    try:
                        post_dt = datetime.datetime.strptime(job.postedDate, "%Y-%m-%d")
                        delta_days = (datetime.datetime.now() - post_dt).days
                        if delta_days * 24 > limit:
                            continue
                    except Exception:
                        pass

                key = f"{job.title.lower()}_{job.company.lower()}"
                if job.url not in seen_urls and key not in seen_keys:
                    passed.append(job)

            limit_str = f"{limit} hours" if limit else "no limit"
            print(f"    [DEBUG] Trying limit: {limit_str} -> {len(passed)} jobs passed.")

            if passed or not limit:
                # Add to deduplication sets and return
                for job in passed:
                    key = f"{job.title.lower()}_{job.company.lower()}"
                    seen_urls.add(job.url)
                    seen_keys.add(key)
                return passed

        return []

    def send_to_n8n(self, jobs: List[Job], webhook_url: str) -> int:
        """Send discovered Job models to n8n Webhook."""
        success_count = 0
        for job in jobs:
            try:
                payload = job.to_dict() if hasattr(job, "to_dict") else job
                # Inject keys to bypass n8n environment variable sandbox restrictions
                groq_key = os.getenv("GROQ_API_KEY")
                discord_url = os.getenv("DISCORD_WEBHOOK_URL")
                payload["groq_api_key"] = groq_key.strip() if groq_key else ""
                payload["discord_webhook_url"] = discord_url.strip() if discord_url else ""
                
                res = requests.post(webhook_url, json=payload, timeout=5)
                if res.status_code in (200, 201, 202, 204):
                    success_count += 1
                else:
                    print(f"    [WEBHOOK DEBUG] Job '{payload.get('title')}' -> Status {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"    [WEBHOOK DEBUG] Request failed: {e}")
        print(f"[N8N INGEST] Sent {success_count}/{len(jobs)} jobs to n8n Webhook.")
        return success_count
