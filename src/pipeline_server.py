#!/usr/bin/env python3
"""
Lightweight Local Pipeline Server on Port 5679
Bypasses n8n JS sandbox restrictions to compile PDF resumes onto disk and post binary PDF attachments to Discord.
"""

import os
import sys
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import notify_discord helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify_discord import send_discord_notification

class PipelineHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path in ["/generate-pdf", "/webhook/generate-pdf"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            
            try:
                data = json.loads(post_data)
                
                # Extract LLM tailored JSON
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

                # Job metadata
                job_info = data.get("job") or data.get("job_info") or {}

                # 1. Ensure output directory
                out_dir = os.path.abspath("output_resumes")
                os.makedirs(out_dir, exist_ok=True)

                # Merge with master source_profile.json for missing sections (e.g. education)
                source_profile_path = os.path.abspath("source_profile.json")
                if os.path.exists(source_profile_path):
                    with open(source_profile_path, "r", encoding="utf-8") as sp_f:
                        master_profile = json.load(sp_f)
                    for k, v in master_profile.items():
                        if k not in tailored_json or not tailored_json[k]:
                            tailored_json[k] = v

                # Ensure personal_info key exists for PDF renderer
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

                # 2. Save tailored JSON
                json_path = os.path.join(out_dir, "tailored_profile.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(tailored_json, f, indent=2)

                # 3. Generate PDF Resume
                pdf_path = os.path.join(out_dir, "Siddharth_Bhople_Resume.pdf")
                cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "generate_pdf.py"), "--profile", json_path, "--output", pdf_path]
                subprocess.run(cmd, check=True)
                print(f"[PIPELINE SERVER] Compiled PDF Resume: {pdf_path}")

                # 4. Send Discord Notification WITH Binary PDF Attachment
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
                self.end_headers()
                self.wfile.write(json.dumps(res_payload).encode("utf-8"))

            except Exception as e:
                print(f"[PIPELINE SERVER ERROR] {e}", file=sys.stderr)
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress standard HTTP logs

def run_server(port=8765):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, PipelineHandler)
    print(f"[PIPELINE SERVER] Listening on http://127.0.0.1:{port}/generate-pdf...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
