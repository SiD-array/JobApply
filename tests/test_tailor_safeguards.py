#!/usr/bin/env python3
"""
Unit tests for the Stage 3 LLM Resume Tailoring validation and safeguards.
"""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.resume_validator import sanitize_and_validate_resume_json
from src.tailor_llm import merge_tailored_resume

class TestTailorSafeguards(unittest.TestCase):

    def setUp(self):
        # Load Siddharth's master profile
        with open("source_profile.json", "r", encoding="utf-8") as f:
            self.source_profile = json.load(f)

        # Mock valid LLM response matching prompt schema
        self.valid_response = {
            "tailored_summary": "Expert AI engineer specialized in cloud governance.",
            "matched_keywords": ["Python", "AWS", "FastAPI"],
            "tailored_experience": [
                {
                    "company": "BSH Hausgeräte GmbH (Bosch Group)",
                    "title": "DAAD RISE Professional Scholar AI Engineering Intern (Pre-Development)",
                    "bullet_points": [
                        "Accomplished RMSE target +/-500g, as measured by automated testing, by engineering TDMS processing pipelines in Python."
                    ]
                }
            ],
            "featured_projects": [
                {
                    "name": "Autonomous Cloud Governance",
                    "bullet_points": [
                        "Accomplished cost reduction from 412% to 0%, as measured by billing metrics, by designing cloud-native multi-agent platforms."
                    ]
                }
            ]
        }

    def test_valid_json_parsing(self):
        raw_output = json.dumps(self.valid_response)
        validated = sanitize_and_validate_resume_json(raw_output, self.source_profile)
        self.assertEqual(validated["tailored_summary"], "Expert AI engineer specialized in cloud governance.")

    def test_markdown_fence_stripping(self):
        raw_output = f"```json\n{json.dumps(self.valid_response)}\n```"
        validated = sanitize_and_validate_resume_json(raw_output, self.source_profile)
        self.assertEqual(validated["tailored_summary"], "Expert AI engineer specialized in cloud governance.")

    def test_conversational_text_stripping(self):
        raw_output = f"Here is the result:\n{json.dumps(self.valid_response)}\nHope this helps!"
        validated = sanitize_and_validate_resume_json(raw_output, self.source_profile)
        self.assertEqual(validated["tailored_summary"], "Expert AI engineer specialized in cloud governance.")

    def test_missing_required_key(self):
        invalid_data = self.valid_response.copy()
        del invalid_data["matched_keywords"]
        raw_output = json.dumps(invalid_data)
        with self.assertRaises(KeyError):
            sanitize_and_validate_resume_json(raw_output, self.source_profile)

    def test_hallucinated_company_name(self):
        invalid_data = json.loads(json.dumps(self.valid_response))
        invalid_data["tailored_experience"][0]["company"] = "Google DeepMind"  # Not in source profile!
        raw_output = json.dumps(invalid_data)
        with self.assertRaises(ValueError) as ctx:
            sanitize_and_validate_resume_json(raw_output, self.source_profile)
        self.assertIn("Google DeepMind", str(ctx.exception))

    def test_hallucinated_project_name(self):
        invalid_data = json.loads(json.dumps(self.valid_response))
        invalid_data["featured_projects"][0]["name"] = "Gemini Ultra Orchestrator"  # Not in source profile!
        raw_output = json.dumps(invalid_data)
        with self.assertRaises(ValueError) as ctx:
            sanitize_and_validate_resume_json(raw_output, self.source_profile)
        self.assertIn("Gemini Ultra Orchestrator", str(ctx.exception))

    def test_resume_merge_logic(self):
        merged = merge_tailored_resume(self.source_profile, self.valid_response)
        
        # Verify summary was updated
        self.assertEqual(merged["summary"], "Expert AI engineer specialized in cloud governance.")
        
        # Verify experience bullets were updated
        bsh_exp = [e for e in merged["experience"] if "BSH Hausgeräte" in e["company"]][0]
        self.assertIn("Accomplished RMSE target +/-500g", bsh_exp["bullet_points"][0])
        
        # Verify projects bullets were updated
        cloud_proj = [p for p in merged["projects"] if p["name"] == "Autonomous Cloud Governance"][0]
        self.assertIn("Accomplished cost reduction", cloud_proj["bullet_points"][0])

        # Verify education was preserved without modifications
        self.assertEqual(len(merged["education"]), len(self.source_profile["education"]))
        self.assertEqual(merged["education"][0]["degree"], self.source_profile["education"][0]["degree"])


if __name__ == "__main__":
    unittest.main()
