"""
Shared Data Models for the Job Discovery Engine.
Normalizes all job board payloads into a standardized schema.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Job:
    """Standardized Job Model representing a job posting across all providers."""
    title: str
    company: str
    location: str
    employmentType: str       # Full-time, Part-time, Contract, Internship
    experienceLevel: str      # Entry Level, Mid-Level, Senior
    description: str
    url: str
    postedDate: str           # YYYY-MM-DD format
    salary: str               # e.g., "$120,000 - $150,000 / year" or "Not specified"
    source: str               # Provider name: LinkedIn, WellFound, Greenhouse, Lever, Ashby, Workday

    def to_dict(self) -> Dict[str, Any]:
        """Convert Job instance to standard JSON dictionary."""
        return asdict(self)


@dataclass
class SearchQuery:
    """Configurable Search Query parameters passed to Providers."""
    keywords: List[str] = field(default_factory=lambda: ["AI Engineer", "Machine Learning Engineer", "Software Engineer"])
    location: str = "United States"
    remote_only: bool = True
    experience_levels: List[str] = field(default_factory=lambda: ["Entry Level", "Internship", "Associate"])
    target_companies: List[str] = field(default_factory=list)  # Specific company slugs for Greenhouse/Lever/Ashby
    limit_per_provider: int = 10
    max_age_hours: Optional[int] = None

