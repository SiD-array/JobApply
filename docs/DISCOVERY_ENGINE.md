# 🔍 Configurable Job Discovery Engine Architecture

The **Job Discovery Engine** is an extensible, multi-provider job search and normalization framework built for JobApply. It enables parallel job discovery across enterprise career portals, startup job boards, and global tech feeds, normalizing every job posting into a single standardized data model.

---

## 🎯 Architecture Overview

```
                                +---------------------------+
                                |    SearchQuery Config     |
                                +---------------------------+
                                              |
                                              v
+---------------------------------------------------------------------------------------------------+
|                                       DISCOVERY ENGINE                                            |
|                                   (src/discovery/engine.py)                                       |
+---------------------------------------------------------------------------------------------------+
       |                 |                 |                 |                 |                 |
       v                 v                 v                 v                 v                 v
[ LinkedIn ]      [ WellFound ]     [ Greenhouse ]      [ Lever ]        [ Ashby ]        [ Workday ]
Provider          Provider          Provider            Provider         Provider         Provider
       |                 |                 |                 |                 |                 |
       +-----------------+-----------------+-----------------+-----------------+-----------------+
                                              |
                                              v
                                +---------------------------+
                                | Deduplication & Filtering |
                                +---------------------------+
                                              |
                                              v
                                +---------------------------+
                                | Standardized Job Models   |
                                +---------------------------+
```

---

## 📦 Standardized Data Schema (`Job` Model)

Every job posting fetched from any provider is normalized into the shared `Job` model (`src/discovery/models.py`):

```json
{
  "title": "Senior AI Engineer",
  "company": "Stripe",
  "location": "San Francisco, CA / Remote",
  "employmentType": "Full-time",
  "experienceLevel": "Entry Level",
  "description": "Full job description text...",
  "url": "https://boards.greenhouse.io/stripe/jobs/123456",
  "postedDate": "2026-07-21",
  "salary": "$140,000 - $180,000 / year",
  "source": "Greenhouse"
}
```

---

## 🚀 Supported Providers

| Provider | Target Sources | API / Ingestion Method |
| :--- | :--- | :--- |
| **LinkedIn** | Public LinkedIn job search | Guest Search API & HTML parsing |
| **WellFound** | Startup job listings | Startup feed aggregators |
| **Greenhouse** | Stripe, Airbnb, Datadog, Scale AI, etc. | Greenhouse REST API (`boards-api.greenhouse.io`) |
| **Lever** | Palantir, Netflix, Spotify, Framer, etc. | Lever Postings API (`api.lever.co/v0/postings`) |
| **Ashby** | Notion, Linear, OpenAI, Ramp, Replit, etc.| Ashby Job Board API (`api.ashbyhq.com`) |
| **Workday** | NVIDIA, Adobe, Salesforce, Intel, etc. | Workday CXS Enterprise API |

---

## 🛠️ How to Add a New Job Board Provider in 3 Steps

The Discovery Engine uses the **Provider Pattern**. Adding a new job board (e.g. `Indeed`, `Glassdoor`, `ZipRecruiter`) takes 3 quick steps:

### Step 1: Create Provider File
Create `src/discovery/providers/indeed.py`:

```python
from typing import List
from src.discovery.base_provider import BaseJobProvider
from src.discovery.models import Job, SearchQuery

class IndeedProvider(BaseJobProvider):
    def __init__(self):
        super().__init__(name="Indeed")

    def fetch_jobs(self, query: SearchQuery) -> List[Job]:
        jobs = []
        # 1. Fetch postings from target API/feed
        # 2. Convert raw payload into standardized `Job` objects
        jobs.append(Job(
            title="Software Engineer",
            company="Acme Corp",
            location="Remote",
            employmentType="Full-time",
            experienceLevel="Entry Level",
            description="Role details...",
            url="https://indeed.com/viewjob?jk=123",
            postedDate="2026-07-21",
            salary="$120,000 / year",
            source=self.name
        ))
        return jobs
```

### Step 2: Register Provider in Package
In `src/discovery/providers/__init__.py`:

```python
from src.discovery.providers.indeed import IndeedProvider
```

### Step 3: Register in Engine
In `src/discovery/engine.py`:

```python
self.register_provider(IndeedProvider())
```

That's it! The `DiscoveryEngine` will automatically run your new provider in parallel during job search runs.

---

## ⚡ CLI Usage

### Run Multi-Provider Discovery:
```bash
python src/discover_jobs.py --keywords "AI Engineer" "Machine Learning" --limit 5
```

### Filter Specific Providers:
```bash
python src/discover_jobs.py --providers greenhouse lever ashby --limit 3
```

Outputs are automatically normalized, deduplicated, and saved to `samples/discovered_jobs.json`.
