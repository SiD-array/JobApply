"""
LinkedIn Job Board Provider.
Fetches public LinkedIn job postings via RSS feeds and public search APIs.
"""

import sys
import requests
import xml.etree.ElementTree as ET
from typing import List
from datetime import datetime
from src.discovery.base_provider import BaseJobProvider
from src.discovery.models import Job, SearchQuery


class LinkedInProvider(BaseJobProvider):
    """Provider for LinkedIn Public Job Searches."""

    def __init__(self):
        super().__init__(name="LinkedIn")

    def fetch_jobs(self, query: SearchQuery) -> List[Job]:
        jobs = []
        target_kws = query.keywords if query.keywords else ["Software Engineer"]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

        import re

        for kw in target_kws:
            if len(jobs) >= query.limit_per_provider:
                break

            keywords_str = kw.replace(" ", "+")
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords_str}&location={query.location}&start=0"

            try:
                res = requests.get(url, headers=headers, timeout=12)
                if res.status_code == 200 and len(res.text) > 100:
                    card_titles = re.findall(r'<h3 class="base-search-card__title">[\s\S]*?</h3>', res.text)
                    card_companies = re.findall(r'<h4 class="base-search-card__subtitle">[\s\S]*?</h4>', res.text)
                    card_locations = re.findall(r'<span class="job-search-card__location">[\s\S]*?</span>', res.text)
                    card_links = re.findall(r'<a class="base-card__full-link[\s\S]*?href="([^"]+)"', res.text)

                    min_count = min(len(card_titles), len(card_companies), len(card_links))
                    for i in range(min_count):
                        clean_title = re.sub(r'<[^>]+>', '', card_titles[i]).strip()
                        
                        # Apply smart keyword filter
                        if not self.matches_keyword(clean_title, query.keywords):
                            continue

                        clean_company = re.sub(r'<[^>]+>', '', card_companies[i]).strip()
                        clean_location = re.sub(r'<[^>]+>', '', card_locations[i]).strip() if i < len(card_locations) else "United States"
                        link = card_links[i].split('?')[0]

                        # Fetch full detailed description from LinkedIn guest endpoint
                        description_text = f"{clean_title} role at {clean_company}."
                        try:
                            job_id = link.rstrip('/').split('-')[-1]
                            if job_id.isdigit():
                                detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
                                d_res = requests.get(detail_url, headers=headers, timeout=6)
                                if d_res.status_code == 200:
                                    match = re.search(r'<div class="show-more-less-html__markup[\s\S]*?>([\s\S]*?)</div>', d_res.text)
                                    if match:
                                        raw_html = match.group(1)
                                        cleaned = re.sub(r'<[^>]+>', ' ', raw_html)
                                        description_text = ' '.join(cleaned.split())
                        except Exception:
                            pass

                        job = Job(
                            title=clean_title,
                            company=clean_company,
                            location=clean_location,
                            employmentType="Full-time",
                            experienceLevel="Entry Level" if "junior" in clean_title.lower() or "intern" in clean_title.lower() else "Associate",
                            description=description_text,
                            url=link,
                            postedDate=datetime.now().strftime("%Y-%m-%d"),
                            salary="Not specified",
                            source=self.name
                        )
                        jobs.append(job)

                        if len(jobs) >= query.limit_per_provider:
                            break

            except Exception as e:
                print(f"[{self.name} ERROR] Failed to fetch LinkedIn jobs for '{kw}': {e}", file=sys.stderr)

        return jobs
