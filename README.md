# 🚀 Privacy-Focused Job Application & Resume Tailoring Automation Tool

An end-to-end, privacy-first automation pipeline built with **n8n**, **Python (Playwright / Jinja2)**, **Groq (Llama 3.3 70B)**, and **Discord Webhooks**. It evaluates job match fit, tailors candidate bullet points with zero hallucination, compiles 1-page ATS-compliant PDF resumes, notifies Discord, and auto-fills job application forms with Human-in-the-Loop safety.

---

## 🏗️ System Architecture

```
[ 1. Job Discovery ]  ➔  [ 2. Evaluation Gate ]  ➔  [ 3. LLM Resume Tailoring ]  ➔  [ 4. ATS PDF Compiler ]  ➔  [ 5. Discord & Playwright ]
(Webhook / Ingest)     (Python Overlap Score >= 70%) (Groq Llama 3.3 70B)        (LaTeX-Style 1-Page PDF)    (HITL Form Auto-Fill)
```

1. **Job Discovery**: Ingests job postings via webhooks, RSS feeds, or API payloads.
2. **Evaluation Gate (`src/evaluator.py`)**: Extracts tech keywords and calculates match score between candidate profile and target job description. Rejects scores < 70% to save token costs and prevent poor-fit applications.
3. **Resume Tailoring (`src/tailor_llm.py`)**: Uses Groq's high-speed `llama-3.3-70b-versatile` model with strict zero-hallucination constraints to emphasize relevant experience without fabricating work history.
4. **PDF Compiler (`src/generate_pdf.py`)**: Compiles tailored JSON into a single-page ATS-compliant vector PDF resume matching classic LaTeX / Computer Modern typography (`templates/MyResume.pdf`).
5. **Discord & Playwright (`src/notify_discord.py` & `src/apply_playwright.py`)**: Posts rich notification embeds to Discord. On approval, launches headful Chromium to populate applicant inputs (Greenhouse / Lever / Generic forms), uploads PDF resume, and pauses for human review before final submission.

---

## 📁 Repository Structure

```
JobApply/
├── run_pipeline.py        # One-command CLI pipeline wrapper (Stages 2-5)
├── source_profile.json    # Candidate master profile schema
├── src/                   # Core Python application modules
│   ├── evaluator.py       # Stage 2: Fit evaluation & keyword overlap gate
│   ├── tailor_llm.py     # Stage 3: Zero-hallucination LLM resume tailor
│   ├── generate_pdf.py   # Stage 4: 1-page LaTeX-style ATS PDF compiler
│   ├── notify_discord.py # Stage 5: Discord Webhook HITL notification helper
│   └── apply_playwright.py# Stage 5: Headful Playwright ATS form parser & auto-filler
├── workflows/             # Automation workflow files
│   └── n8n_workflow.json  # Complete importable n8n 5-stage workflow JSON
├── templates/             # PDF Resume design templates
│   └── MyResume.pdf       # Reference master PDF resume format
├── samples/               # Sample job payload JSON files
│   ├── sample_job.json
│   └── ai_engineer_job.json
├── requirements.txt       # Python project dependencies
├── .env.example           # Environment variables template
└── README.md              # Project documentation
```

---

## ⚙️ Quick Start Guide

### 1. Clone & Setup Environment
```bash
git clone https://github.com/SiD-array/JobApply.git
cd JobApply

# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

# Install dependencies and Playwright Chromium
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Free Groq API Key (https://console.groq.com)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Discord Webhook URL
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url

# Pipeline Settings
OUTPUT_RESUME_DIR=output_resumes
EVALUATION_THRESHOLD=70.0
```

### 3. Customize Your Master Candidate Profile
Update `source_profile.json` with your real work history, education, projects, and core technical skills.

---

## ⚡ Running the Pipeline

### Option A: One-Command Pipeline CLI (`run_pipeline.py`)
Run all 5 stages end-to-end for a target job URL:
```bash
python run_pipeline.py --url "https://company.greenhouse.io/job/101" --job samples/ai_engineer_job.json
```

### Option B: Test Individual Stages Standalone

1. **Evaluate Job Match Score**:
   ```bash
   python src/evaluator.py --profile source_profile.json --job samples/sample_job.json
   ```

2. **Tailor Resume via Groq**:
   ```bash
   python src/tailor_llm.py --provider groq --job samples/sample_job.json --output output_resumes/tailored_profile.json
   ```

3. **Compile ATS Resume PDF**:
   ```bash
   python src/generate_pdf.py --profile output_resumes/tailored_profile.json --job-id demo_job --output output_resumes/Demo_Resume.pdf
   ```

4. **Send Discord Notification**:
   ```bash
   python src/notify_discord.py --pdf output_resumes/Demo_Resume.pdf --score 85.0
   ```

5. **Launch Playwright Auto-Fill Form**:
   ```bash
   python src/apply_playwright.py --url https://company.greenhouse.io/job/101 --profile source_profile.json --pdf output_resumes/Demo_Resume.pdf
   ```

---

## 🔄 n8n Integration

1. Open your **n8n** dashboard.
2. Click **Workflows** ➔ **Import from File**.
3. Select `workflows/n8n_workflow.json`.
4. Configure `GROQ_API_KEY` and `DISCORD_WEBHOOK_URL` in environment settings.
5. Activate the workflow to ingest and process job postings automatically!

---

## 🔒 Privacy & Safety
- **No Hallucinations**: Strict system prompt constraints prevent the LLM from inventing fake titles, dates, or experience.
- **Human-in-the-Loop**: Playwright runs in headful mode and pauses before clicking the final submit button so you can inspect and verify every form field.
- **Local Control**: All PDF compilation and profile data remain on your local machine.

---

## 📄 License
MIT License. Free for personal and commercial use.
