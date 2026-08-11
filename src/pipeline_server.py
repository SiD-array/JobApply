#!/usr/bin/env python3
"""
Lightweight Local Pipeline & Application Tracker Server on Port 8766
Handles PDF resume compilation, structured job application persistence (applications.json),
Discord Notifications with Binary Attachments, and live status management for the Dashboard.
"""

import os
import sys
import json
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

# Import notify_discord helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_discord import send_discord_notification

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APPLICATIONS_FILE = os.path.join(BASE_DIR, "output_resumes", "applications.json")


def load_applications():
    if os.path.exists(APPLICATIONS_FILE):
        try:
            with open(APPLICATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_applications(apps):
    os.makedirs(os.path.dirname(APPLICATIONS_FILE), exist_ok=True)
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=2)


def delete_application(job_id):
    apps = load_applications()
    updated = [item for item in apps if str(item.get("job_id")) != str(job_id)]
    save_applications(updated)
    return updated


def update_or_add_application(job_info, tailored_data=None, pdf_path=None, status="Approved"):
    apps = load_applications()

    company = job_info.get("company") or (tailored_data.get("header", {}).get("name") if tailored_data else None) or "Target Company"
    title = job_info.get("title") or "Software Engineer"
    raw_job_id = job_info.get("job_id") or f"{company}_{title}".replace(" ", "_").lower()
    job_id = str(raw_job_id)
    apply_url = job_info.get("apply_url") or job_info.get("url") or "#"

    career_url = job_info.get("career_url") or f"https://www.google.com/search?q={urllib.parse.quote(company)}+careers"
    updated_at = datetime.now(timezone.utc).isoformat()

    existing = next((item for item in apps if item.get("job_id") == job_id or (item.get("company") == company and item.get("title") == title)), None)

    if existing:
        existing["status"] = status
        existing["updated_at"] = updated_at
        if apply_url and apply_url != "#":
            existing["apply_url"] = apply_url
        if pdf_path:
            existing["pdf_path"] = pdf_path
        if tailored_data:
            existing["tailored_summary"] = tailored_data.get("tailored_summary", existing.get("tailored_summary", ""))
            existing["matched_keywords"] = tailored_data.get("matched_keywords", existing.get("matched_keywords", []))
    else:
        new_record = {
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": job_info.get("location") or "Remote / USA",
            "apply_url": apply_url,
            "career_url": career_url,
            "match_score": job_info.get("score") or 100,
            "status": status,
            "tailored_summary": (tailored_data or {}).get("tailored_summary", ""),
            "matched_keywords": (tailored_data or {}).get("matched_keywords", []),
            "pdf_path": pdf_path or "output_resumes/Siddharth_Bhople_Resume.pdf",
            "created_at": updated_at,
            "updated_at": updated_at
        }
        apps.insert(0, new_record)

    save_applications(apps)
    return apps


class PipelineHandler(BaseHTTPRequestHandler):

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # 1. API: List Applications for Dashboard
        if parsed.path == "/api/applications":
            apps = load_applications()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(apps).encode("utf-8"))
            return

        # 2. Interactive Approval / Status Change via Web/Discord Click
        if parsed.path in ["/approve", "/reject", "/update-status"]:
            job_id = params.get("job_id", [""])[0]
            new_status = params.get("status", ["Approved" if parsed.path == "/approve" else "Rejected"])[0]

            apps = load_applications()
            target_app = next((item for item in apps if str(item.get("job_id")) == str(job_id)), None)

            if target_app:
                target_app["status"] = new_status
                target_app["updated_at"] = datetime.now(timezone.utc).isoformat()
                save_applications(apps)
                updated_apps = apps
            else:
                job_path = os.path.abspath("output_resumes/current_job.json")
                job_info = {}
                if os.path.exists(job_path):
                    try:
                        with open(job_path, "r", encoding="utf-8") as f:
                            job_info = json.load(f)
                    except Exception:
                        pass

                if not job_info and job_id:
                    job_info = {"job_id": job_id, "company": "Target Company", "title": "Software Engineer"}
                elif job_id:
                    job_info["job_id"] = job_id

                pdf_path = os.path.abspath("output_resumes/Siddharth_Bhople_Resume.pdf")
                tailored_json_path = os.path.abspath("output_resumes/tailored_profile.json")
                tailored_data = {}
                if os.path.exists(tailored_json_path):
                    try:
                        with open(tailored_json_path, "r", encoding="utf-8") as f:
                            tailored_data = json.load(f)
                    except Exception:
                        pass

                updated_apps = update_or_add_application(job_info, tailored_data, pdf_path, status=new_status)
                target_app = next((item for item in updated_apps if str(item.get("job_id")) == str(job_id)), updated_apps[0] if updated_apps else {})

            title = target_app.get("title", "Software Engineer")
            company = target_app.get("company", "Company")
            apply_url = target_app.get("apply_url", "#")
            career_url = target_app.get("career_url", "#")
            current_status = target_app.get("status", new_status)

            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JobApply — Application Status Updated</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }}
  .card {{ background: #1e293b; border: 1px solid #334155; padding: 36px; border-radius: 20px; text-align: center; max-width: 520px; width: 100%; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }}
  .status-badge {{ display: inline-block; padding: 6px 16px; border-radius: 9999px; font-weight: 700; font-size: 14px; text-transform: uppercase; margin-bottom: 16px; background: #0284c7; color: #ffffff; }}
  h1 {{ color: #ffffff; margin: 0 0 8px 0; font-size: 24px; font-weight: 700; }}
  .subtitle {{ color: #94a3b8; font-size: 15px; margin-bottom: 24px; line-height: 1.5; }}
  .details-box {{ background: #0f172a; border-radius: 12px; padding: 16px; margin-bottom: 24px; text-align: left; border: 1px solid #334155; }}
  .details-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
  .details-row:last-child {{ margin-bottom: 0; }}
  .label {{ color: #64748b; font-weight: 600; }}
  .value {{ color: #f1f5f9; font-weight: 600; word-break: break-all; }}
  .btn-group {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 20px; }}
  .btn {{ padding: 10px 18px; border-radius: 10px; font-weight: 600; font-size: 13px; text-decoration: none; transition: all 0.2s; border: none; cursor: pointer; }}
  .btn-primary {{ background: #3b82f6; color: #ffffff; }}
  .btn-primary:hover {{ background: #2563eb; }}
  .btn-success {{ background: #10b981; color: #ffffff; }}
  .btn-success:hover {{ background: #059669; }}
  .btn-secondary {{ background: #334155; color: #94a3b8; }}
  .btn-secondary:hover {{ background: #475569; color: #ffffff; }}
  .btn-danger {{ background: #ef4444; color: #ffffff; }}
  .btn-danger:hover {{ background: #dc2626; }}
</style>
</head>
<body>
  <div class="card">
    <div class="status-badge">Status: {current_status}</div>
    <h1>Job Application Saved</h1>
    <p class="subtitle">Structured job details, company links, and your tailored ATS resume are tracked in your JobApply database.</p>

    <div class="details-box">
      <div class="details-row"><span class="label">Company:</span><span class="value">{company}</span></div>
      <div class="details-row"><span class="label">Role Title:</span><span class="value">{title}</span></div>
      <div class="details-row"><span class="label">Status:</span><span class="value">{current_status}</span></div>
    </div>

    <div class="btn-group">
      <a href="{apply_url}" target="_blank" class="btn btn-primary">🔗 Open Apply Page</a>
      <a href="{career_url}" target="_blank" class="btn btn-secondary">🏢 Company Career Portal</a>
      <a href="http://localhost:3000" target="_blank" class="btn btn-success">📊 View Dashboard</a>
    </div>

    <div style="margin-top: 24px; font-size: 12px; color: #64748b;">Update Status:</div>
    <div class="btn-group" style="margin-top: 8px;">
      <a href="/update-status?job_id={job_id}&status=Applied" class="btn btn-success">✅ Applied</a>
      <a href="/update-status?job_id={job_id}&status=Not+Applied" class="btn btn-secondary">⏳ Not Applied</a>
      <a href="/update-status?job_id={job_id}&status=Interviewing" class="btn btn-primary">💼 Interviewing</a>
      <a href="/update-status?job_id={job_id}&status=Rejected" class="btn btn-danger">❌ Rejected</a>
    </div>
  </div>
</body>
</html>"""

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        # API: Delete Application from Datasheet
        if parsed.path in ["/api/delete-application", "/api/applications/delete"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(post_data)
                job_id = str(payload.get("job_id", ""))
                delete_application(job_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "deleted_job_id": job_id}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # API: Update Status from Dashboard via POST
        if parsed.path in ["/api/update-status", "/api/applications/update-status"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(post_data)
                job_id = str(payload.get("job_id", ""))
                new_status = payload.get("status", "Applied")

                apps = load_applications()
                target = next((item for item in apps if item.get("job_id") == job_id), None)
                if target:
                    target["status"] = new_status
                    target["updated_at"] = datetime.now(timezone.utc).isoformat()
                    save_applications(apps)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "job_id": job_id, "new_status": new_status}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # Core Pipeline Engine PDF Generation Handler
        if parsed.path in ["/generate-pdf", "/webhook/generate-pdf"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(post_data)

                content_raw = ""
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]

                if "choices" in data:
                    content_raw = data["choices"][0]["message"]["content"]
                elif "tailored_summary" in data:
                    content_raw = data
                else:
                    content_raw = data.get("content", post_data)

                if isinstance(content_raw, str):
                    tailored_json = json.loads(content_raw)
                else:
                    tailored_json = content_raw

                job_info = data.get("job") or data.get("job_info") or {}

                out_dir = os.path.abspath("output_resumes")
                os.makedirs(out_dir, exist_ok=True)

                # Save current job for approval tracking
                current_job_path = os.path.join(out_dir, "current_job.json")
                with open(current_job_path, "w", encoding="utf-8") as f:
                    json.dump(job_info, f, indent=2)

                source_profile_path = os.path.abspath("source_profile.json")
                if os.path.exists(source_profile_path):
                    with open(source_profile_path, "r", encoding="utf-8") as sp_f:
                        master_profile = json.load(sp_f)
                    for k, v in master_profile.items():
                        if k not in tailored_json or not tailored_json[k]:
                            tailored_json[k] = v

                if "personal_info" not in tailored_json and "header" in tailored_json:
                    h = tailored_json["header"]
                    name_parts = (h.get("name") or "Siddharth Bhople").split(" ")
                    tailored_json["personal_info"] = {
                        "first_name": name_parts[0],
                        "last_name": name_parts[-1] if len(name_parts) > 1 else "",
                        "email": h.get("email", "sid.work0403@gmail.com"),
                        "phone": h.get("phone", "585-625-8123"),
                        "location": h.get("location", "Rochester, NY"),
                        "linkedin": h.get("linkedin", "https://linkedin.com/in/siddharth-bhople/"),
                        "github": h.get("github", "https://github.com/SiD-array")
                    }

                json_path = os.path.join(out_dir, "tailored_profile.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(tailored_json, f, indent=2)

                pdf_path = os.path.join(out_dir, "Siddharth_Bhople_Resume.pdf")
                venv_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "Scripts", "python.exe"))
                py_exe = venv_py if os.path.exists(venv_py) else sys.executable

                cmd = [py_exe, os.path.join(os.path.dirname(__file__), "generate_pdf.py"), "--profile", json_path, "--output", pdf_path]
                subprocess.run(cmd, check=True)
                print(f"[PIPELINE SERVER] Compiled PDF Resume: {pdf_path}")

                # Save initial application record as "Approved"
                update_or_add_application(job_info, tailored_json, pdf_path, status="Approved")

                # Send Discord Notification WITH Binary PDF Attachment
                webhook_url = data.get("discord_webhook_url") or os.getenv("DISCORD_WEBHOOK_URL")
                discord_sent = False
                if webhook_url:
                    eval_info = {
                        "company": job_info.get("company") or tailored_json.get("header", {}).get("name") or "NewsBreak",
                        "title": job_info.get("title") or "Software Engineer, ML Infra",
                        "score": job_info.get("score") or 100,
                        "job_id": job_info.get("job_id") or "job_101"
                    }
                    discord_sent = send_discord_notification(
                        webhook_url=webhook_url,
                        eval_result=eval_info,
                        job_info=job_info,
                        pdf_path=pdf_path,
                        tailored_data=tailored_json
                    )
                    print(f"[PIPELINE SERVER] Discord Notification with PDF Attachment sent: {discord_sent}")

                res_payload = {
                    "status": "success",
                    "pdf_path": pdf_path,
                    "json_path": json_path,
                    "discord_sent": discord_sent,
                    "tailored_summary": tailored_json.get("tailored_summary", ""),
                    "matched_keywords": tailored_json.get("matched_keywords", [])
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(res_payload).encode("utf-8"))

            except Exception as e:
                print(f"[PIPELINE SERVER ERROR] {e}", file=sys.stderr)
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def run_server(port=8766):
    HTTPServer.allow_reuse_address = True
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, PipelineHandler)
    print(f"[PIPELINE SERVER] Listening on http://127.0.0.1:{port}/generate-pdf...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
