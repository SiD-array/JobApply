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

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DIRECTORY)


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

        # Static Files
        else:
            super().do_GET()

    def do_POST(self):
        if self.path in ["/api/update-status", "/api/applications/update-status"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                import json
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
