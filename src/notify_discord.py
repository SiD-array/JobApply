#!/usr/bin/env python3
"""
Discord Human-in-the-Loop Notification Helper
Sends rich embed notifications to a Discord channel via Webhook.
"""

import sys
import os
import json
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()


def send_discord_notification(webhook_url: str, job_info: dict, pdf_path: str, score: float) -> bool:
    """Send job application notification embed to Discord via Webhook."""
    company = job_info.get("company", "Unknown Company")
    title = job_info.get("title", "Software Engineer")
    apply_url = job_info.get("apply_url", "N/A")
    job_id = job_info.get("job_id", "unknown")

    embed = {
        "title": f"🎯 New Job Match: {title} @ {company}",
        "description": f"Tailored resume PDF generated and ready for auto-fill approval.",
        "url": apply_url if apply_url.startswith("http") else None,
        "color": 3066993 if score >= 80 else 15844367,  # Green if >=80, Gold if <80
        "fields": [
          {"name": "🏢 Company", "value": company, "inline": True},
          {"name": "💼 Title", "value": title, "inline": True},
          {"name": "📊 Match Score", "value": f"**{score}%**", "inline": True},
          {"name": "🔗 Job Link", "value": apply_url or "N/A", "inline": False},
          {"name": "📄 Resume PDF", "value": f"`{pdf_path}`", "inline": False}
        ],
        "footer": {
            "text": f"Job ID: {job_id} | Stage 5 Human-in-the-Loop Gate"
        }
    }

    payload = {
        "username": "JobApply AI Assistant",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3855/3855328.png",
        "embeds": [embed]
    }

    # Send with multipart PDF attachment if file exists
    if pdf_path and os.path.exists(pdf_path):
        filename = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as f:
            files = {"file": (filename, f, "application/pdf")}
            data = {"payload_json": json.dumps(payload)}
            response = requests.post(webhook_url, data=data, files=files)
    else:
        response = requests.post(webhook_url, json=payload)

    if response.status_code in (200, 204):
        print("[DISCORD] Notification and PDF attachment sent successfully!")
        return True
    else:
        print(f"[DISCORD ERROR] Failed to send notification: {response.status_code} - {response.text}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Send Human-in-the-Loop job match notification to Discord.")
    parser.add_argument("--webhook", help="Discord Webhook URL (or reads DISCORD_WEBHOOK_URL env var)")
    parser.add_argument("--job", help="Path to job JSON file")
    parser.add_argument("--score", type=float, default=85.0, help="Match score percentage")
    parser.add_argument("--pdf", required=True, help="Path to compiled PDF resume")
    args = parser.parse_args()

    webhook_url = args.webhook or os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[DISCORD ERROR] Missing Discord Webhook URL. Set DISCORD_WEBHOOK_URL in .env or pass --webhook", file=sys.stderr)
        sys.exit(1)

    if args.job and os.path.exists(args.job):
        with open(args.job, "r", encoding="utf-8") as f:
            job_data = json.load(f)
    else:
        job_data = {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "apply_url": "https://example.com/apply",
            "job_id": "demo_101"
        }

    send_discord_notification(webhook_url, job_data, args.pdf, args.score)


if __name__ == "__main__":
    main()
