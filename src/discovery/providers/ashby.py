"""
Ashby Job Board Provider.
Fetches jobs directly from Ashby public job board APIs (api.ashbyhq.com).
"""

import sys
import requests
from typing import List
from datetime import datetime
from src.discovery.base_provider import BaseJobProvider
from src.discovery.models import Job, SearchQuery

DEFAULT_COMPANIES = ["notion", "linear", "openai", "ramp", "replit"]


class AshbyProvider(BaseJobProvider):
    """Provider for Ashby Job Portals."""

    def __init__(self):
        super().__init__(name="Ashby")

    def fetch_jobs(self, query: SearchQuery) -> List[Job]:
        jobs = []
        companies = query.target_companies or DEFAULT_COMPANIES

        for company in companies:
            if len(jobs) >= query.limit_per_provider:
                break

            url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
            try:
                res = requests.get(url, timeout=10)
                if res.status_code != 200:
                    continue

                data = res.json()
                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    if query.keywords and not any(kw.lower() in title.lower() for kw in query.keywords):
                        continue

                    location_name = item.get("locationName", "Remote")
                    description = item.get("descriptionHtml", title)
                    employment_type = item.get("employmentType", "Full-time")

                    job = Job(
                        title=title,
                        company=company.capitalize(),
                        location=location_name,
                        employmentType=employment_type,
                        experienceLevel="Entry Level" if "junior" in title.lower() or "intern" in title.lower() else "Mid-Level",
                        description=description,
                        url=item.get("jobUrl", f"https://jobs.ashbyhq.com/{company}/{item.get('id')}"),
                        postedDate=datetime.now().strftime("%Y-%m-%d"),
                        salary="Not specified",
                        source=self.name
                    )
                    jobs.append(job)

                    if len(jobs) >= query.limit_per_provider:
                        break

            except Exception as e:
                print(f"[{self.name} ERROR] Failed to fetch jobs for {company}: {e}", file=sys.stderr)

        return jobs
