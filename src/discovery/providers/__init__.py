"""
Job Providers Package.
Exposes all 6 supported Job Board Providers:
- LinkedIn
- Simplify
- Greenhouse
- Lever
- Ashby
- Workday
"""

from src.discovery.providers.linkedin import LinkedInProvider
from src.discovery.providers.simplify import SimplifyProvider
from src.discovery.providers.greenhouse import GreenhouseProvider
from src.discovery.providers.lever import LeverProvider
from src.discovery.providers.ashby import AshbyProvider
from src.discovery.providers.workday import WorkdayProvider

__all__ = [
    "LinkedInProvider",
    "SimplifyProvider",
    "GreenhouseProvider",
    "LeverProvider",
    "AshbyProvider",
    "WorkdayProvider"
]
