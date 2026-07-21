"""
Greenhouse Job Board Provider.
Fetches jobs directly from Greenhouse public APIs (boards-api.greenhouse.io).
"""

import sys
import requests
from typing import List
from datetime import datetime
from src.discovery.base_provider import BaseJobProvider
from src.discovery.models import Job, SearchQuery

DEFAULT_COMPANIES = ["airbnb", "stripe", "datadog", "scaleai", "discord", "figma"]


class GreenhouseProvider(BaseJobProvider):
    """Provider for Greenhouse Career Portals."""

    def __init__(self):
        super().__init__(name="Greenhouse")

    def fetch_jobs(self, query: SearchQuery) -> List[Job]:
        jobs = []
        companies = query.target_companies or DEFAULT_COMPANIES

        for company in companies:
            if len(jobs) >= query.limit_per_provider:
                break

            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
            try:
                res = requests.get(url, timeout=10)
                if res.status_code != 200:
                    continue

                data = res.json()
                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    # Filter by keywords if provided
                    if query.keywords and not any(kw.lower() in title.lower() for kw in query.keywords):
                        continue

                    location_name = item.get("location", {}).get("name", "Remote")
                    description = item.get("content", title)
                    updated_at = item.get("updated_at", "")
                    posted_date = updated_at[:10] if updated_at else datetime.now().strftime("%Y-%m-%d")

                    job = Job(
                        title=title,
                        company=company.capitalize(),
                        location=location_name,
                        employmentType="Full-time",
                        experienceLevel="Entry Level" if "junior" in title.lower() or "intern" in title.lower() else "Mid-Level",
                        description=description,
                        url=item.get("absolute_url", f"https://boards.greenhouse.io/{company}/jobs/{item.get('id')}"),
                        postedDate=posted_date,
                        salary="Not specified",
                        source=self.name
                    )
                    jobs.append(job)

                    if len(jobs) >= query.limit_per_provider:
                        break

            except Exception as e:
                print(f"[{self.name} ERROR] Failed to fetch jobs for {company}: {e}", file=sys.stderr)

        return jobs
