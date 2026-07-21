#!/usr/bin/env python3
"""
End-to-End One-Click Pipeline Execution Script
Given a job URL and job description (or JSON file), runs:
1. Stage 2: Fit Evaluation Gate (evaluator.py)
2. Stage 3: LLM Resume Tailoring (tailor_llm.py with Groq)
3. Stage 4: 1-Page ATS PDF Compilation (generate_pdf.py)
4. Stage 5: Discord HITL Notification (notify_discord.py)
5. Stage 5: Headful Playwright ATS Form Auto-Fill (apply_playwright.py)
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path


def run_command(cmd_args: list) -> str:
    """Execute python subcommand using current virtual environment python."""
    python_exe = sys.executable
    full_cmd = [python_exe] + cmd_args
    print(f"\n[RUNNING] {' '.join(full_cmd)}")
    result = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="End-to-End Job Application & Resume Tailoring Pipeline CLI")
    parser.add_argument("--url", required=True, help="Job Application URL (Greenhouse / Lever / Webpage)")
    parser.add_argument("--job", help="Path to job JSON or Markdown description file")
    parser.add_argument("--title", default="Software / AI Engineer", help="Job Title if providing text")
    parser.add_argument("--company", default="Target Company", help="Company Name if providing text")
    parser.add_argument("--provider", default="groq", choices=["groq", "cerebras", "openrouter"], help="AI Provider")
    parser.add_argument("--force-apply", action="store_true", help="Proceed even if evaluation fit score is < 70%")
    args = parser.parse_args()

    # Build job object
    if args.job and os.path.exists(args.job):
        job_file_path = args.job
    else:
        # Create temp job file
        job_file_path = "temp_job.json"
        job_payload = {
            "job_id": "job_apply_target",
            "title": args.title,
            "company": args.company,
            "description": f"Job Title: {args.title}\nCompany: {args.company}\nURL: {args.url}",
            "apply_url": args.url
        }
        with open(job_file_path, "w", encoding="utf-8") as f:
            json.dump(job_payload, f, indent=2)

    print("="*60)
    print("🚀 STARTING AUTOMATED JOB APPLICATION PIPELINE")
    print("="*60)

    # 1. Stage 2: Fit Evaluation Gate
    print("\n--- STAGE 2: EVALUATION GATE ---")
    eval_script = os.path.join("src", "evaluator.py")
    eval_out = run_command([eval_script, "--profile", "source_profile.json", "--job", job_file_path])
    eval_json = json.loads(eval_out)
    score = eval_json.get("score", 0.0)
    passed = eval_json.get("passed", False)
    print(f"📊 Fit Match Score: {score}% | Recommendation: {'PASS' if passed else 'REJECT'}")

    if not passed and not args.force_apply:
        print(f"❌ Match score {score}% is below threshold of 70%. Halting pipeline to save time & credits.")
        print("Tip: Use --force-apply flag to proceed anyway.")
        sys.exit(0)

    # 2. Stage 3: LLM Resume Tailoring
    print("\n--- STAGE 3: LLM RESUME TAILORING ---")
    tailored_json_path = os.path.join("output_resumes", "tailored_profile.json")
    tailor_script = os.path.join("src", "tailor_llm.py")
    run_command([tailor_script, "--provider", args.provider, "--job", job_file_path, "--output", tailored_json_path])

    # 3. Stage 4: PDF Compilation
    print("\n--- STAGE 4: ATS PDF RESUME COMPILATION ---")
    output_pdf_path = os.path.join("output_resumes", "Siddharth_Bhople_Resume.pdf")
    pdf_script = os.path.join("src", "generate_pdf.py")
    run_command([pdf_script, "--profile", tailored_json_path, "--job-id", "Siddharth_Bhople", "--output", output_pdf_path])
    print(f"📄 ATS Resume compiled to: {os.path.abspath(output_pdf_path)}")

    # 4. Stage 5: Discord Notification
    print("\n--- STAGE 5: DISCORD HITL NOTIFICATION ---")
    discord_script = os.path.join("src", "notify_discord.py")
    try:
        run_command([discord_script, "--pdf", output_pdf_path, "--score", str(score), "--job", job_file_path])
    except Exception as e:
        print(f"⚠️ Discord notification warning: {e}")

    # 5. Stage 5: Playwright Auto-Fill Form & Review
    print("\n--- STAGE 5: PLAYWRIGHT ATS FORM AUTO-FILL ---")
    print("Launching Chromium browser to fill application inputs...")
    apply_script = os.path.join("src", "apply_playwright.py")
    run_command([apply_script, "--url", args.url, "--profile", "source_profile.json", "--pdf", output_pdf_path])

    print("\n✅ PIPELINE EXECUTION COMPLETE!")


if __name__ == "__main__":
    main()
