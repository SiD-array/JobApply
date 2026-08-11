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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for company in companies:
            if len(jobs) >= query.limit_per_provider:
                break

            # 1. Fetch lightweight summary list without full HTML content payload
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
            try:
                res = requests.get(url, headers=headers, timeout=(5, 15))
                if res.status_code != 200:
                    continue

                data = res.json()
                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    if not self.matches_keyword(title, query.keywords):
                        continue

                    job_id = item.get("id")
                    location_name = item.get("location", {}).get("name", "Remote / USA")
                    updated_at = item.get("updated_at", "")
                    posted_date = updated_at[:10] if updated_at else datetime.now().strftime("%Y-%m-%d")

                    # 2. Fetch full details only for matching jobs
                    description = title
                    if job_id:
                        detail_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}?content=true"
                        try:
                            d_res = requests.get(detail_url, headers=headers, timeout=10)
                            if d_res.status_code == 200:
                                d_json = d_res.json()
                                description = d_json.get("content", title)
                        except Exception:
                            pass

                    job = Job(
                        title=title,
                        company=company.capitalize(),
                        location=location_name,
                        employmentType="Full-time",
                        experienceLevel="Entry Level" if any(k in title.lower() for k in ["junior", "intern", "new grad", "associate"]) else "Mid-Level",
                        description=description,
                        url=item.get("absolute_url", f"https://boards.greenhouse.io/{company}/jobs/{job_id}"),
                        postedDate=posted_date,
                        salary="Not specified",
                        source=self.name
                    )
                    jobs.append(job)

                    if len(jobs) >= query.limit_per_provider:
                        break

            except Exception as e:
                print(f"[{self.name} WARN] Timeout or connection error fetching Greenhouse for {company}: {e}", file=sys.stderr)

        return jobs
