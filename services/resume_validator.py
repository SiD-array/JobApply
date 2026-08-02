#!/usr/bin/env python3
"""
Sanitizer and validator utility for resume tailoring output.
Strips markdown and validates schema & candidate factual constraints.
"""

import json
import re
from typing import Dict, Any

def sanitize_and_validate_resume_json(raw_llm_output: str, source_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes LLM response by stripping markdown fences and validates
    against target JSON schema and hallucination safeguards.
    
    Args:
        raw_llm_output: Raw text output from LLM.
        source_profile: Dict representing original source_profile.json.
        
    Returns:
        Dict: Validated and sanitized tailored resume details.
        
    Raises:
        ValueError: If JSON is invalid or hallucinated content is detected.
        KeyError: If required keys are missing.
    """
    text = raw_llm_output.strip()

    # 1. Strip markdown fences if present (e.g. ```json ... ``` or ``` ... ```)
    if text.startswith("```"):
        match = re.search(r"^(?:```[a-zA-Z0-9]*\n?)(.*?)(?:\n?```)$", text, re.DOTALL | re.MULTILINE)
        if match:
            text = match.group(1).strip()
            
    # Remove any leading/trailing conversational text if the JSON is surrounded by text
    if not (text.startswith("{") and text.endswith("}")):
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    # 2. Parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}. Raw content: {text[:200]}")

    # 3. Validate required keys
    required_keys = ["tailored_summary", "matched_keywords", "tailored_experience", "featured_projects"]
    for key in required_keys:
        if key not in data:
            raise KeyError(f"Missing required key in LLM output: '{key}'")

    # 4. Safeguard: Verify companies in tailored experience match source profile
    source_companies = {exp["company"].strip().lower() for exp in source_profile.get("experience", [])}
    for item in data.get("tailored_experience", []):
        company = item.get("company")
        if not company:
            raise KeyError("Tailored experience item is missing 'company' key")
        if company.strip().lower() not in source_companies:
            raise ValueError(f"Hallucination Detected: Company '{company}' in LLM output is not in source profile")

    # 5. Safeguard: Verify project names in featured projects match source profile
    source_projects = {proj["name"].strip().lower() for proj in source_profile.get("projects", [])}
    for item in data.get("featured_projects", []):
        name = item.get("name")
        if not name:
            raise KeyError("Featured project item is missing 'name' key")
        if name.strip().lower() not in source_projects:
            raise ValueError(f"Hallucination Detected: Project '{name}' in LLM output is not in source profile")

    return data
