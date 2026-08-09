"""
Simplify Jobs Provider.
Fetches and parses the community new grad job postings from their popular public GitHub repository.
"""

import sys
import requests
import re
import datetime
from typing import List
from src.discovery.base_provider import BaseJobProvider
from src.discovery.models import Job, SearchQuery


class SimplifyProvider(BaseJobProvider):
    """Provider for Simplify.jobs Public GitHub Listings."""

    def __init__(self):
        super().__init__(name="Simplify")

    def fetch_jobs(self, query: SearchQuery) -> List[Job]:
        jobs = []
        url = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code != 200:
                print(f"[{self.name} ERROR] Failed to fetch raw GitHub file: Status {res.status_code}", file=sys.stderr)
                return []

            raw_markdown = res.text

            # Parse markdown HTML table rows
            tr_matches = re.findall(r'<tr>([\s\S]*?)</tr>', raw_markdown)
            current_company = "Unknown"

            for tr in tr_matches:
                # Find all td columns inside this tr
                td_matches = re.findall(r'<td>([\s\S]*?)</td>', tr)
                if len(td_matches) != 5:
                    continue

                col1, col2, col3, col4, col5 = td_matches

                # Clean Company Name
                clean_company = re.sub(r'<[^>]+>', '', col1).strip()
                # If it's a sub-listing, inherit company name
                if not clean_company or clean_company in ("↳", "↳", "↳"):
                    company_name = current_company
                else:
                    # Remove FAANG+ fire emoji and whitespace
                    company_name = clean_company.replace("🔥", "").strip()
                    current_company = company_name

                # Clean Role Title
                title = re.sub(r'<[^>]+>', '', col2).strip()

                # Apply smart keyword filter
                if not self.matches_keyword(title, query.keywords):
                    continue

                # Clean Location
                location = re.sub(r'<[^>]+>', ' ', col3).strip()
                location = re.sub(r'\s+', ' ', location)

                # Extract App URL
                app_url_match = re.search(r'href="([^"]+)"', col4)
                app_url = app_url_match.group(1) if app_url_match else "https://simplify.jobs"
                # Exclude internal simplify profiles if it's not the direct application link
                if "simplify.jobs/p/" in app_url and len(re.findall(r'href="([^"]+)"', col4)) > 1:
                    # Try finding another link that goes directly to the company site
                    links = re.findall(r'href="([^"]+)"', col4)
                    for l in links:
                        if "simplify.jobs/p/" not in l:
                            app_url = l
                            break

                # Clean Age & Parse Posted Date
                age_str = re.sub(r'<[^>]+>', '', col5).strip().lower()
                days = 0
                if "d" in age_str:
                    try:
                        days = int(re.sub(r'\D', '', age_str))
                    except Exception:
                        pass
                elif "w" in age_str:
                    try:
                        days = int(re.sub(r'\D', '', age_str)) * 7
                    except Exception:
                        pass
                elif "mo" in age_str or "m" in age_str:
                    try:
                        days = int(re.sub(r'\D', '', age_str)) * 30
                    except Exception:
                        pass

                posted_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

                job = Job(
                    title=title,
                    company=company_name,
                    location=location,
                    employmentType="Full-time",
                    experienceLevel="Entry Level",
                    description=f"{title} position at {company_name} sourced from Simplify.jobs.",
                    url=app_url,
                    postedDate=posted_date,
                    salary="Not specified",
                    source=self.name
                )
                jobs.append(job)

                if len(jobs) >= query.limit_per_provider:
                    break

        except Exception as e:
            print(f"[{self.name} ERROR] Failed parsing Simplify.jobs GitHub repo: {e}", file=sys.stderr)

        return jobs
