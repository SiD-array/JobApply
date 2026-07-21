#!/usr/bin/env python3
"""
Simple Local Web Server for JobApply React Dashboard
Serves dashboard/index.html on http://localhost:3000
"""

import http.server
import socketserver
import webbrowser
import os

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


def main():
    print(f"🚀 [DASHBOARD] Starting JobApply React Dashboard Server on http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        webbrowser.open(f"http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Stopping Dashboard Server.")


if __name__ == "__main__":
    main()
