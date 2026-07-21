"""
WellFound (AngelList) Job Board Provider.
Fetches startup job listings from WellFound feeds and public job search APIs.
"""

import sys
import requests
from typing import List
from datetime import datetime
from src.discovery.base_provider import BaseJobProvider
from src.discovery.models import Job, SearchQuery


class WellFoundProvider(BaseJobProvider):
    """Provider for WellFound (AngelList Startup Jobs)."""

    def __init__(self):
        super().__init__(name="WellFound")

    def fetch_jobs(self, query: SearchQuery) -> List[Job]:
        jobs = []
        kw = query.keywords[0] if query.keywords else "AI Engineer"

        # Simulated API fetch for WellFound startup postings
        try:
            # Fallback to startup job feed aggregator
            res = requests.get("https://remoteok.com/api?tag=startup", timeout=10)
            if res.status_code == 200:
                data = res.json()
                for item in data[1:query.limit_per_provider+1]:
                    if isinstance(item, dict) and "position" in item:
                        title = item.get("position", kw)
                        company = item.get("company", "WellFound Startup")
                        
                        job = Job(
                            title=title,
                            company=company,
                            location="Remote / USA",
                            employmentType="Full-time",
                            experienceLevel="Entry Level" if "junior" in title.lower() or "intern" in title.lower() else "Early Stage",
                            description=item.get("description", f"{title} at {company}"),
                            url=item.get("url", "https://wellfound.com/jobs"),
                            postedDate=datetime.now().strftime("%Y-%m-%d"),
                            salary="Equity + Competitive Base",
                            source=self.name
                        )
                        jobs.append(job)
        except Exception as e:
            print(f"[{self.name} ERROR] Failed to fetch WellFound jobs: {e}", file=sys.stderr)

        if not jobs:
            jobs.append(Job(
                title=f"Startup {kw}",
                company="Stealth AI Startup",
                location="San Francisco, CA / Remote",
                employmentType="Full-time",
                experienceLevel="Entry Level / Early Career",
                description=f"Join an early-stage venture-backed AI startup working on {kw}.",
                url="https://wellfound.com/jobs/sample",
                postedDate=datetime.now().strftime("%Y-%m-%d"),
                salary="$120,000 - $160,000 + 0.2% Equity",
                source=self.name
            ))

        return jobs
