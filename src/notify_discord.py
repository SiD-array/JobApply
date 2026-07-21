#!/usr/bin/env python3
"""
Stage 5: Redesigned Discord Human-in-the-Loop Notification Helper
Sends rich, formatted job match approval cards to Discord Webhooks with binary file attachments.
Displays:
  - Company, Role, Location, Source
  - Interview Probability, Overall Score
  - Matched Skills, Missing Skills
  - Resume & Cover Letter Readiness
  - Quick LLM Summary
  - Interactive Action Links (Approve, Reject, Open Job Posting, Open Resume)
"""

import sys
import os
import json
import argparse
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()


def send_discord_notification(
    webhook_url: str,
    eval_result: dict,
    job_info: dict,
    pdf_path: str = None,
    cover_pdf_path: str = None
) -> bool:
    """Send redesigned rich embed notification and PDF file attachments to Discord."""

    company = job_info.get("company") or eval_result.get("company") or "Target Company"
    title = job_info.get("title") or eval_result.get("title") or "Software / AI Engineer"
    location = job_info.get("location") or "Remote / USA"
    source = job_info.get("source") or "Career Portal"
    apply_url = job_info.get("apply_url") or job_info.get("url") or "#"
    job_id = job_info.get("job_id") or eval_result.get("job_id") or "job_101"

    score = eval_result.get("score", 85)
    interview_prob = eval_result.get("interviewProbability", "High")
    matched_skills = eval_result.get("matchedSkills") or eval_result.get("matched_skills") or []
    missing_skills = eval_result.get("missingSkills") or eval_result.get("missing_skills") or []
    reason = eval_result.get("reason", "Strong alignment across target roles, technical stack, and career level.")

    # Determine Embed Color
    if score >= 80:
        color = 3066993  # Vibrant Green
        prob_emoji = "🔥 High"
    elif score >= 70:
        color = 15844367  # Gold / Amber
        prob_emoji = "⚡ Medium"
    else:
        color = 15158332  # Crimson Red
        prob_emoji = "❄️ Low"

    matched_str = ", ".join(matched_skills[:8]) if matched_skills else "None"
    missing_str = ", ".join(missing_skills[:5]) if missing_skills else "None"

    resume_status = f"✅ `{os.path.basename(pdf_path)}`" if (pdf_path and os.path.exists(pdf_path)) else "❌ Not generated"
    cover_status = f"✅ `{os.path.basename(cover_pdf_path)}`" if (cover_pdf_path and os.path.exists(cover_pdf_path)) else "❌ Not generated"

    embed = {
        "title": f"🎯 Job Match Approval Request: {title} @ {company}",
        "description": f"**Quick Summary**:\n*{reason}*\n\n---",
        "url": apply_url if apply_url.startswith("http") else None,
        "color": color,
        "fields": [
            {"name": "🏢 Company", "value": f"**{company}**", "inline": True},
            {"name": "💼 Role", "value": f"**{title}**", "inline": True},
            {"name": "📍 Location", "value": location, "inline": True},

            {"name": "📌 Source", "value": f"`{source}`", "inline": True},
            {"name": "📊 Overall Score", "value": f"**{score} / 100**", "inline": True},
            {"name": "🎯 Interview Prob", "value": f"**{prob_emoji}**", "inline": True},

            {"name": "✅ Matched Skills", "value": f"`{matched_str}`", "inline": False},
            {"name": "⚠️ Missing Skills", "value": f"`{missing_str}`" if missing_skills else "`None`", "inline": False},

            {"name": "📄 Resume Ready", "value": resume_status, "inline": True},
            {"name": "✉️ Cover Letter Ready", "value": cover_status, "inline": True},

            {
                "name": "⚡ Quick Actions & Links",
                "value": (
                    f"🔗 [**Open Job Posting**]({apply_url})\n"
                    f"✅ [**Approve Application**](http://localhost:5678/webhook/approve?job_id={job_id})\n"
                    f"❌ [**Reject Application**](http://localhost:5678/webhook/reject?job_id={job_id})"
                ),
                "inline": False
            }
        ],
        "footer": {
            "text": f"Job ID: {job_id} • Stage 5 Human-in-the-Loop Gate",
            "icon_url": "https://cdn-icons-png.flaticon.com/512/3855/3855328.png"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload = {
        "username": "JobApply AI Assistant",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3855/3855328.png",
        "embeds": [embed]
    }

    # Prepare multipart binary PDF file attachments
    files = {}
    if pdf_path and os.path.exists(pdf_path):
        files["file1"] = (os.path.basename(pdf_path), open(pdf_path, "rb"), "application/pdf")
    if cover_pdf_path and os.path.exists(cover_pdf_path):
        files["file2"] = (os.path.basename(cover_pdf_path), open(cover_pdf_path, "rb"), "application/pdf")

    try:
        if files:
            data = {"payload_json": json.dumps(payload)}
            response = requests.post(webhook_url, data=data, files=files)
        else:
            response = requests.post(webhook_url, json=payload)

        if response.status_code in (200, 204):
            print("[DISCORD SUCCESS] Redesigned notification embed & PDF attachments sent successfully!")
            return True
        else:
            print(f"[DISCORD ERROR] Webhook failed ({response.status_code}): {response.text}", file=sys.stderr)
            return False
    finally:
        for f_tuple in files.values():
            try:
                f_tuple[1].close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Send Redesigned Discord Job Approval Card CLI")
    parser.add_argument("--webhook", help="Discord Webhook URL (reads DISCORD_WEBHOOK_URL env if omitted)")
    parser.add_argument("--job", help="Path to job JSON file")
    parser.add_argument("--eval", help="Path to evaluation result JSON file")
    parser.add_argument("--pdf", help="Path to tailored PDF resume")
    parser.add_argument("--cover", help="Path to tailored PDF cover letter")
    args = parser.parse_args()

    webhook_url = args.webhook or os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[DISCORD ERROR] Missing DISCORD_WEBHOOK_URL.", file=sys.stderr)
        sys.exit(1)

    job_info = {}
    if args.job and os.path.exists(args.job):
        with open(args.job, "r", encoding="utf-8") as f:
            job_info = json.load(f)

    eval_info = {
        "score": 92,
        "interviewProbability": "High",
        "matchedSkills": ["Python", "PyTorch", "FastAPI", "AWS", "TensorFlow"],
        "missingSkills": ["Kubernetes"],
        "reason": "Exceptional alignment across primary target roles (AI Software Engineer), technical stack, and early-career level."
    }
    if args.eval and os.path.exists(args.eval):
        with open(args.eval, "r", encoding="utf-8") as f:
            eval_info = json.load(f)

    send_discord_notification(webhook_url, eval_info, job_info, pdf_path=args.pdf, cover_pdf_path=args.cover)


if __name__ == "__main__":
    main()
