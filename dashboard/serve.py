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

        # 3. Static Files
        else:
            super().do_GET()


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
