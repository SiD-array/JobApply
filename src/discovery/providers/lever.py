"""
Lever Job Board Provider.
Fetches jobs directly from Lever public APIs (api.lever.co).
"""

import sys
import requests
from typing import List
from datetime import datetime
from src.discovery.base_provider import BaseJobProvider
from src.discovery.models import Job, SearchQuery

DEFAULT_COMPANIES = ["palantir", "netflix", "spotify", "framer"]


class LeverProvider(BaseJobProvider):
    """Provider for Lever Career Portals."""

    def __init__(self):
        super().__init__(name="Lever")

    def fetch_jobs(self, query: SearchQuery) -> List[Job]:
        jobs = []
        companies = query.target_companies or DEFAULT_COMPANIES

        for company in companies:
            if len(jobs) >= query.limit_per_provider:
                break

            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            try:
                res = requests.get(url, timeout=10)
                if res.status_code != 200:
                    continue

                postings = res.json()
                for item in postings:
                    title = item.get("text", "")
                    if query.keywords and not any(kw.lower() in title.lower() for kw in query.keywords):
                        continue

                    categories = item.get("categories", {})
                    location_name = categories.get("location", "Remote")
                    commitment = categories.get("commitment", "Full-time")
                    description = item.get("descriptionPlain", title)
                    created_at = item.get("createdAt")
                    posted_date = datetime.fromtimestamp(created_at / 1000).strftime("%Y-%m-%d") if created_at else datetime.now().strftime("%Y-%m-%d")

                    job = Job(
                        title=title,
                        company=company.capitalize(),
                        location=location_name,
                        employmentType=commitment,
                        experienceLevel="Entry Level" if "junior" in title.lower() or "intern" in title.lower() else "Mid-Level",
                        description=description,
                        url=item.get("hostedUrl", f"https://jobs.lever.co/{company}/{item.get('id')}"),
                        postedDate=posted_date,
                        salary=item.get("salaryRange", {}).get("text", "Not specified"),
                        source=self.name
                    )
                    jobs.append(job)

                    if len(jobs) >= query.limit_per_provider:
                        break

            except Exception as e:
                print(f"[{self.name} ERROR] Failed to fetch jobs for {company}: {e}", file=sys.stderr)

        return jobs
