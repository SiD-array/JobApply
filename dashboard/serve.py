#!/usr/bin/env python3
"""
Lightweight API & Web Server for JobApply React Dashboard
Serves dashboard/index.html and dynamically handles local file API endpoints:
  - /api/jobs -> Serves samples/discovered_jobs.json
  - /api/insights -> Serves output_resumes/career_insights.json
"""

import http.server
import socketserver
import webbrowser
import os
import sys

import subprocess
import threading
import json
import time

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DIRECTORY)

DISCOVERY_STATUS = {
    "status": "idle",
    "message": "Ready to discover jobs",
    "last_run": None
}


def run_discovery_task(limit=3, providers="linkedin,simplify,greenhouse,lever,ashby,workday"):
    global DISCOVERY_STATUS
    DISCOVERY_STATUS["status"] = "running"
    DISCOVERY_STATUS["message"] = f"Searching {providers} for entry-level roles..."
    DISCOVERY_STATUS["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        venv_python = os.path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            venv_python = sys.executable

        cmd = [
            venv_python,
            os.path.join(PROJECT_ROOT, "src", "discover_jobs.py"),
            "--webhook", "none",
            "--providers", providers,
            "--limit", str(limit)
        ]

        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if proc.returncode == 0:
            DISCOVERY_STATUS["status"] = "completed"
            DISCOVERY_STATUS["message"] = "Discovery complete! Jobs sent to n8n & Discord."
        else:
            DISCOVERY_STATUS["status"] = "error"
            DISCOVERY_STATUS["message"] = f"Discovery error: {proc.stderr[:120]}"
    except Exception as e:
        DISCOVERY_STATUS["status"] = "error"
        DISCOVERY_STATUS["message"] = str(e)


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Handler for static dashboard files and dynamic live APIs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # 1. API: Live Discovered Jobs
        if self.path == "/api/jobs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            jobs_file = os.path.join(PROJECT_ROOT, "samples", "discovered_jobs.json")
            if os.path.exists(jobs_file):
                with open(jobs_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"[]")

        # 2. API: Live Career Insights & Skill Gaps
        elif self.path == "/api/insights":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            insights_file = os.path.join(PROJECT_ROOT, "output_resumes", "career_insights.json")
            if os.path.exists(insights_file):
                with open(insights_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"{}")

        # 3. API: Persistent Applications Store & Tracker
        elif self.path == "/api/applications":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            apps_file = os.path.join(PROJECT_ROOT, "output_resumes", "applications.json")
            if os.path.exists(apps_file):
                with open(apps_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"[]")

        # 4. API: Job Discovery Status
        elif self.path == "/api/discovery-status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(DISCOVERY_STATUS).encode("utf-8"))

        # Static Files
        else:
            super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        import urllib.parse
        clean_path = urllib.parse.urlparse(self.path).path.rstrip("/")

        # 1-Click Discovery Trigger API
        if clean_path in ["/api/trigger-discovery", "/api/discovery/start"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data) if post_data.strip() else {}
                limit = int(payload.get("limit", 3))
                providers = payload.get("providers", "linkedin,simplify,greenhouse,lever,ashby,workday")

                if DISCOVERY_STATUS.get("status") == "running":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "already_running", "message": "Discovery task is already in progress!"}).encode("utf-8"))
                    return

                thread = threading.Thread(target=run_discovery_task, kwargs={"limit": limit, "providers": providers}, daemon=True)
                thread.start()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "started", "message": f"Discovery task started in background across {providers}!"}).encode("utf-8"))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        if clean_path in ["/api/delete-application", "/api/applications/delete"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(post_data)
                job_id = str(payload.get("job_id", ""))

                apps_file = os.path.join(PROJECT_ROOT, "output_resumes", "applications.json")
                if os.path.exists(apps_file):
                    with open(apps_file, "r", encoding="utf-8") as f:
                        apps = json.load(f)
                    apps = [item for item in apps if str(item.get("job_id")) != job_id and str(item.get("id")) != job_id]
                    with open(apps_file, "w", encoding="utf-8") as f:
                        json.dump(apps, f, indent=2)

                disc_file = os.path.join(PROJECT_ROOT, "samples", "discovered_jobs.json")
                if os.path.exists(disc_file):
                    try:
                        with open(disc_file, "r", encoding="utf-8") as f:
                            jobs = json.load(f)
                        if isinstance(jobs, list):
                            jobs = [j for j in jobs if str(j.get("job_id")) != job_id and str(j.get("id")) != job_id]
                            with open(disc_file, "w", encoding="utf-8") as f:
                                json.dump(jobs, f, indent=2)
                    except Exception:
                        pass

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "deleted_job_id": job_id}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        if self.path in ["/api/update-status", "/api/applications/update-status"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                from datetime import datetime, timezone
                payload = json.loads(post_data)
                job_id = str(payload.get("job_id", ""))
                new_status = payload.get("status", "Applied")

                apps_file = os.path.join(PROJECT_ROOT, "output_resumes", "applications.json")
                apps = []
                if os.path.exists(apps_file):
                    with open(apps_file, "r", encoding="utf-8") as f:
                        apps = json.load(f)

                target = next((item for item in apps if item.get("job_id") == job_id), None)
                if target:
                    target["status"] = new_status
                    target["updated_at"] = datetime.now(timezone.utc).isoformat()
                    with open(apps_file, "w", encoding="utf-8") as f:
                        json.dump(apps, f, indent=2)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "job_id": job_id, "new_status": new_status}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def main():
    print(f"[DASHBOARD] Starting JobApply Live React Dashboard Server on http://localhost:{PORT}")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        webbrowser.open(f"http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Stopping Dashboard Server.")


if __name__ == "__main__":
    main()
