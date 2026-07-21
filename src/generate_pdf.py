#!/usr/bin/env python3
"""
Stage 4: PDF Compiler Node Script
Compiles tailored profile JSON into a clean, single-column, ATS-compliant PDF resume
matching the exact typography and visual layout of Resume/MyResume.pdf (LaTeX / Computer Modern style).
"""

import sys
import os
import json
import argparse
from pathlib import Path

# LaTeX / Jake's Resume style HTML/CSS template matching MyResume.pdf layout
MY_RESUME_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: letter;
    margin: 0.3in 0.4in 0.3in 0.4in;
  }
  body {
    font-family: 'Times New Roman', Times, 'Georgia', serif;
    color: #000000;
    font-size: 9.5pt;
    line-height: 1.18;
    margin: 0;
    padding: 0;
  }
  
  /* Header */
  .header {
    text-align: center;
    margin-bottom: 6px;
  }
  .header h1 {
    font-size: 20pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin: 0 0 1px 0;
    color: #000000;
  }
  .header .address {
    font-size: 9pt;
    margin-bottom: 2px;
  }
  .header .contact-links {
    font-size: 9pt;
  }
  .header a {
    color: #000000;
    text-decoration: none;
  }

  /* Section Title */
  .section-title {
    font-size: 11pt;
    font-weight: 700;
    text-transform: capitalize;
    border-bottom: 1px solid #000000;
    margin-top: 7px;
    margin-bottom: 4px;
    padding-bottom: 1px;
    color: #000000;
  }

  /* Flex Rows for Education, Experience, Projects */
  .row-top {
    display: flex;
    justify-content: space-between;
    font-weight: 700;
    font-size: 9.5pt;
  }
  .row-sub {
    display: flex;
    justify-content: space-between;
    font-style: italic;
    font-size: 9pt;
    color: #111111;
    margin-bottom: 2px;
  }

  /* Block Spacing */
  .edu-block {
    margin-bottom: 4px;
  }
  .exp-block {
    margin-bottom: 5px;
  }
  .proj-block {
    margin-bottom: 5px;
  }

  /* Bullet Lists */
  ul {
    margin: 1px 0 3px 14px;
    padding: 0;
  }
  li {
    margin-bottom: 1.5px;
    text-align: justify;
  }

  /* Technical Skills Category List */
  .skill-category {
    margin-bottom: 2px;
    font-size: 9pt;
  }
  .skill-category strong {
    font-weight: 700;
  }
</style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <h1>{{ personal_info.first_name }} {{ personal_info.last_name }}</h1>
    {% if personal_info.location %}
    <div class="address">{{ personal_info.location }}</div>
    {% endif %}
    <div class="contact-links">
      {% if personal_info.phone %}📞 {{ personal_info.phone }} &nbsp;{% endif %}
      {% if personal_info.email %}✉ <a href="mailto:{{ personal_info.email }}">{{ personal_info.email }}</a> &nbsp;{% endif %}
      {% if personal_info.linkedin %}🔗 <a href="{{ personal_info.linkedin }}">{{ personal_info.linkedin | replace('https://', '') }}</a> &nbsp;{% endif %}
      {% if personal_info.github %}💻 <a href="{{ personal_info.github }}">{{ personal_info.github | replace('https://', '') }}</a>{% endif %}
    </div>
  </div>

  <!-- Education -->
  {% if education %}
  <div class="section-title">Education</div>
  {% for edu in education %}
  <div class="edu-block">
    <div class="row-top">
      <span>{{ edu.institution }}</span>
      <span>{% if edu.start_date %}{{ edu.start_date }} &ndash; {% endif %}{{ edu.graduation_year }}</span>
    </div>
    <div class="row-sub">
      <span>{{ edu.degree }}{% if edu.gpa %}, GPA: {{ edu.gpa }}{% endif %}</span>
      <span>{{ edu.location }}</span>
    </div>
  </div>
  {% endfor %}
  {% endif %}

  <!-- Experience -->
  {% if experience %}
  <div class="section-title">Experience</div>
  {% for job in experience %}
  <div class="exp-block">
    <div class="row-top">
      <span>{{ job.company }}</span>
      <span>{{ job.start_date }} &ndash; {{ job.end_date }}</span>
    </div>
    <div class="row-sub">
      <span>{{ job.title }}</span>
      <span>{{ job.location }}</span>
    </div>
    <ul>
      {% for bullet in job.bullet_points %}
      <li>{{ bullet }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endfor %}
  {% endif %}

  <!-- Projects -->
  {% if projects %}
  <div class="section-title">Projects</div>
  {% for proj in projects %}
  <div class="proj-block">
    <div class="row-top">
      <span>{{ proj.name }} | <em>{{ proj.technologies | join(', ') }}</em></span>
      <span>{{ proj.date }}</span>
    </div>
    <ul>
      {% for bullet in proj.bullet_points %}
      <li>{{ bullet }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endfor %}
  {% endif %}

  <!-- Technical Skills -->
  {% if core_skills %}
  <div class="section-title">Technical Skills</div>
  {% if skill_categories %}
    {% for cat_name, cat_skills in skill_categories.items() %}
    <div class="skill-category">
      <strong>{{ cat_name }}:</strong> {{ cat_skills | join(', ') }}
    </div>
    {% endfor %}
  {% else %}
    <div class="skill-category">
      <strong>Skills:</strong> {{ core_skills | join(', ') }}
    </div>
  {% endif %}
  {% endif %}

</body>
</html>
"""


def render_html(profile_data: dict) -> str:
    """Render HTML string matching MyResume.pdf layout."""
    # Organize skills into categories matching Siddharth's resume layout if present
    skills = profile_data.get("core_skills", [])
    if "skill_categories" not in profile_data:
        # Auto-categorize skills if flat array is provided
        languages = [s for s in skills if s in ['Python', 'Java', 'JavaScript', 'C/C++', 'C#/.NET', 'SQL', 'HTML/CSS', 'C', 'C++']]
        aiml = [s for s in skills if s in ['Scikit-learn', 'TensorFlow', 'PyTorch', 'XGBoost', 'NumPy', 'Pandas', 'Feature Engineering', 'PCA', 'RUL Modeling']]
        frameworks = [s for s in skills if s in ['React', 'Node.js', 'FastAPI', 'Streamlit', 'Vite', 'Git', 'GitHub', 'VS Code', 'MATLAB']]
        cloud_db = [s for s in skills if s in ['AWS', 'Firebase', 'MySQL', 'PostgreSQL', 'MongoDB', 'Docker']]
        
        categories = {}
        if languages: categories["Languages"] = languages
        if aiml: categories["AI/ML"] = aiml
        if frameworks: categories["Frameworks & Tools"] = frameworks
        if cloud_db: categories["Cloud & Databases"] = cloud_db
        
        # Any remaining skills
        allocated = set(languages + aiml + frameworks + cloud_db)
        other = [s for s in skills if s not in allocated]
        if other: categories["Other Skills"] = other

        profile_data["skill_categories"] = categories

    try:
        from jinja2 import Template
        template = Template(MY_RESUME_HTML_TEMPLATE)
        return template.render(**profile_data)
    except ImportError:
        # Fallback simple template logic
        pass


def compile_pdf_playwright(html_content: str, output_pdf_path: str):
    """Compile HTML content to PDF file using Playwright."""
    from playwright.sync_api import sync_playwright

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="load")
        page.pdf(
            path=output_pdf_path,
            format="Letter",
            print_background=True,
            margin={
                "top": "0.4in",
                "right": "0.45in",
                "bottom": "0.4in",
                "left": "0.45in"
            }
        )
        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Compile tailored profile JSON into ATS-compliant PDF matching MyResume.pdf layout.")
    parser.add_argument("--profile", default="source_profile.json", help="Path to tailored profile JSON file")
    parser.add_argument("--job-id", default="default", help="Job ID for file naming")
    parser.add_argument("--output", help="Path to output PDF file")
    args = parser.parse_args()

    # Read profile data from file or stdin
    if args.profile:
        with open(args.profile, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    else:
        raw_data = json.load(sys.stdin)

    profile_data = raw_data.get("tailoredProfile", raw_data)

    # Normalize key aliases (personal_info vs contact)
    if "personal_info" not in profile_data and "contact" in profile_data:
        profile_data["personal_info"] = profile_data["contact"]
    elif "contact" not in profile_data and "personal_info" in profile_data:
        profile_data["contact"] = profile_data["personal_info"]

    # Determine output path
    if args.output:
        out_path = args.output
    else:
        out_dir = Path("./output_resumes")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / f"{args.job_id}_Resume.pdf")

    # Render HTML and compile PDF
    html_content = render_html(profile_data)
    compile_pdf_playwright(html_content, out_path)

    result = {
        "status": "success",
        "job_id": args.job_id,
        "pdf_path": os.path.abspath(out_path)
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
