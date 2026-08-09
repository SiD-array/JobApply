 # Role & Goal
You are an expert Systems Architect and Automation Engineer specializing in n8n, Python, and LLM integrations. 
Your goal is to help me design, build, and deploy an end-to-end, privacy-focused Job Application & Resume Tailoring Automation Tool using n8n, Python (Playwright/Typst), and an LLM API.

---

## System Overview & Architecture
The system follows a modular, 5-stage pipeline:
1. Job Discovery (Scrape / Ingest job postings via API or HTTP Webhook)
2. Evaluation Gate (Semantic scoring against candidate profile)
3. Resume Tailoring Engine (Structured JSON manipulation using LLM with zero-hallucination constraints)
4. PDF Document Generation (Compile tailored JSON into clean, ATS-compliant PDF)
5. Submission & Form Parsing (Browser automation using Playwright with Human-in-the-Loop approval)

---

## Core Data Schema

### 1. Candidate Source Profile (`source_profile.json`)
```json
{
  "personal_info": {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "phone": "+1234567890",
    "linkedin": "[https://linkedin.com/in/janedoe](https://linkedin.com/in/janedoe)",
    "github": "[https://github.com/janedoe](https://github.com/janedoe)"
  },
  "core_skills": ["Python", "PostgreSQL", "Docker", "REST APIs", "LLM Integration"],
  "experience": [
    {
      "company": "Tech Solutions",
      "title": "Software Engineer",
      "location": "Remote",
      "start_date": "2023-01",
      "end_date": "Present",
      "bullet_points": [
        "Architected RESTful microservices processing 1M daily requests.",
        "Optimized PostgreSQL queries, reducing execution latency by 40%.",
        "Built automated CI/CD pipelines using GitHub Actions and Docker."
      ]
    }
  ],
  "education": [
    {
      "degree": "B.S. Computer Science",
      "institution": "State University",
      "graduation_year": "2022"
    }
  ]
}

Detailed Stage Implementation Plan
Stage 1: Job Discovery Node
n8n Node Type: HTTP Request or Cron Trigger

Action: Fetch active listings from a source (e.g., local database, webhook payload from JobSpy, or career portal API).

Output Data Structure:

JSON
{
  "job_id": "12345",
  "title": "Backend Engineer",
  "company": "Acme Corp",
  "description": "Full raw job description text...",
  "apply_url": "[https://company.greenhouse.io/job/12345](https://company.greenhouse.io/job/12345)"
}
Stage 2: Evaluation Gate (Filtering)
n8n Node Type: Code Node (Python or JS) followed by an If Node

Logic:

Extract hard requirements (skills, years of experience keywords) from the job description.

Compute a preliminary overlap score between candidate core_skills and job requirements.

Reject jobs with a score < 70% to save token costs and prevent poor-fit applications.

Stage 3: LLM Resume Tailoring Node
n8n Node Type: Advanced AI Agent Node connected to Model Node (gpt-4o or claude-3-5-sonnet)

System Prompt for LLM:

You are an expert ATS (Applicant Tracking System) optimizer and professional resume writer.
You will receive candidate profile data (source_profile.json) and a job_description.

STRICT CONSTRAINTS:

NEVER invent, fabricate, or exaggerate work experience, metrics, companies, titles, or dates.

You may ONLY reorder, highlight, or rephrase bullet points from source_profile.json to emphasize relevance to the target job.

Align technical terminology with keywords from the job description where factually accurate.

Output MUST strictly adhere to the requested JSON structure. No prose outside JSON.

Output Format:
Return a modified JSON object matching source_profile.json, featuring updated bullet_points and a tailored 2-sentence summary.

Stage 4: PDF Compiler Node
n8n Node Type: Execute Command (or external microservice HTTP call)

Action:

Receive the tailored JSON output from Stage 3.

Pass data into a single-column, clean HTML template or a Typst script.

Compile into a standard ATS-readable PDF file (/tmp/resumes/{job_id}_Resume.pdf).

Stage 5: Form Parsing & Human-in-the-Loop (HITL) Gate
n8n Node Type: Wait Node / Slack Node / Telegram Node

Action:

Send a notification to the candidate (e.g., via Telegram/Slack or local dashboard) with the tailored resume PDF, match score, and job link.

Provide approval buttons: [Approve & Apply] or [Reject].

On Approval:
Trigger a local Python script running Playwright in headful mode to open apply_url, auto-fill form inputs (First Name, Last Name, Email, upload PDF), and pause for human review before final submit click.

Deliverables Required
Please guide me step-by-step to implement this workflow. Start by generating:

The exact n8n workflow JSON structure or node-by-node setup instructions for Stages 1–3.

The Python script template using Playwright to handle standard ATS forms (Greenhouse / Lever).