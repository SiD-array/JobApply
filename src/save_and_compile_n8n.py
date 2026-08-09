#!/usr/bin/env python3
"""
Stage 4 Helper for n8n:
Saves LLM-tailored JSON to output_resumes/tailored_profile.json
and compiles single-page ATS PDF resume to output_resumes/Siddharth_Bhople_Resume.pdf.
"""

import sys
import os
import json
import subprocess

def main():
    try:
        raw_input = sys.stdin.read().strip()
        if not raw_input:
            print(json.dumps({"status": "error", "message": "No input provided on stdin"}))
            sys.exit(1)

        input_data = json.loads(raw_input)
        
        # Extract content object from Ollama/Groq response
        content_raw = ""
        if isinstance(input_data, list) and len(input_data) > 0:
            input_data = input_data[0]

        if "choices" in input_data:
            content_raw = input_data["choices"][0]["message"]["content"]
        elif "tailored_summary" in input_data:
            content_raw = input_data
        else:
            content_raw = input_data.get("content", raw_input)

        if isinstance(content_raw, str):
            tailored_json = json.loads(content_raw)
        else:
            tailored_json = content_raw

        # Ensure output directory exists
        out_dir = os.path.abspath("output_resumes")
        os.makedirs(out_dir, exist_ok=True)

        # Save tailored JSON
        json_path = os.path.join(out_dir, "tailored_profile.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(tailored_json, f, indent=2)

        # Compile PDF Resume
        pdf_path = os.path.join(out_dir, "Siddharth_Bhople_Resume.pdf")
        cmd = [sys.executable, "src/generate_pdf.py", "--profile", json_path, "--output", pdf_path]
        subprocess.run(cmd, check=True)

        res = {
            "status": "success",
            "json_path": json_path,
            "pdf_path": pdf_path,
            "tailored_summary": tailored_json.get("tailored_summary", ""),
            "matched_keywords": tailored_json.get("matched_keywords", []),
            "ats_coverage_score": tailored_json.get("ats_coverage_score", "9/10"),
            "project_order_rationale": tailored_json.get("project_order_rationale", "")
        }
        print(json.dumps(res))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
