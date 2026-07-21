"""
Abstract Base Provider Class.
Every job board provider (LinkedIn, WellFound, Greenhouse, Lever, Ashby, Workday)
inherits from BaseJobProvider and implements the `fetch_jobs` method.
"""

from abc import ABC, abstractmethod
from typing import List
from src.discovery.models import Job, SearchQuery


class BaseJobProvider(ABC):
    """Abstract Interface for Job Board Providers."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch_jobs(self, query: SearchQuery) -> List[Job]:
        """
        Fetch and normalize job postings for a given SearchQuery.
        Must return a list of standardized `Job` objects.
        """
        pass
