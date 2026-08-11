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

    EXCLUDED_SENIORITY_KEYWORDS = ["senior", "sr.", "sr ", "staff", "principal", "lead", "director", "head of", "vp", "manager", "architect"]

    def is_senior_role(self, title: str) -> bool:
        """Check if job title requires senior/staff/lead experience not suitable for early career/new grad."""
        t_lower = title.lower()
        for kw in self.EXCLUDED_SENIORITY_KEYWORDS:
            if kw in t_lower:
                # Exception: allow if explicitly flagged for Junior / New Grad / Intern
                if any(x in t_lower for x in ["junior", "new grad", "intern", "university"]):
                    return False
                return True
        return False

    def matches_keyword(self, title: str, keywords: List[str]) -> bool:
        """
        Check if the job title matches any of the target search keywords.
        Enforces strict seniority exclusions for early career candidates.
        """
        if self.is_senior_role(title):
            return False

        if not keywords:
            return True
            
        t_lower = title.lower()
        
        for kw in keywords:
            kw_lower = kw.strip().lower()
            
            # Smart rule 1: ML Engineering New Grad
            if kw_lower == "ml engineering new grad":
                has_ml = "ml" in t_lower or "machine learning" in t_lower
                has_grad = "new grad" in t_lower or "new graduate" in t_lower or "university graduate" in t_lower or "university grad" in t_lower
                if has_ml and has_grad:
                    return True
                    
            # Smart rule 2: AI Engineering New Grad
            elif kw_lower == "ai engineering new grad":
                has_ai = "ai " in t_lower or " ai" in t_lower or "artificial intelligence" in t_lower or "genai" in t_lower or "generative ai" in t_lower
                has_grad = "new grad" in t_lower or "new graduate" in t_lower or "university graduate" in t_lower or "university grad" in t_lower
                if has_ai and has_grad:
                    return True
                    
            # Smart rule 3: Data Engineer New Grad
            elif kw_lower == "data engineer new grad":
                has_data = "data" in t_lower
                has_eng = "engineer" in t_lower or "developer" in t_lower
                has_grad = "new grad" in t_lower or "new graduate" in t_lower or "university graduate" in t_lower or "university grad" in t_lower
                if has_data and has_eng and has_grad:
                    return True
                    
            # Smart rule 4: Software Engineer New Grad
            elif kw_lower == "software engineer new grad":
                has_swe = "software" in t_lower or "swe" in t_lower or "application" in t_lower or "full stack" in t_lower or "frontend" in t_lower or "backend" in t_lower or "systems" in t_lower
                has_eng = "engineer" in t_lower or "developer" in t_lower
                has_grad = "new grad" in t_lower or "new graduate" in t_lower or "university graduate" in t_lower or "university grad" in t_lower
                if has_swe and has_eng and has_grad:
                    return True
                    
            # Smart rule 5: AI Research Engineer
            elif kw_lower == "ai research engineer":
                has_ai = "ai " in t_lower or " ai" in t_lower or "artificial intelligence" in t_lower or "machine learning" in t_lower or "ml" in t_lower
                has_research = "research" in t_lower or "scientist" in t_lower
                has_eng = "engineer" in t_lower or "developer" in t_lower or "researcher" in t_lower
                if has_ai and has_research and (has_eng or "scientist" in t_lower):
                    return True
            
            # Fallback to simple substring match
            elif kw_lower in t_lower:
                return True
                
        return False
