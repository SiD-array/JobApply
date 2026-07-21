#!/usr/bin/env python3
"""
Stage 5: Playwright ATS Form Parser & Human-in-the-Loop Auto-Filler
Launches headful Playwright browser, navigates to application URL, fills candidate
information & uploads PDF resume, then pauses for human review before submission.
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError


def fill_greenhouse_form(page: Page, profile: dict, pdf_path: str):
    """Auto-fill Greenhouse ATS form inputs."""
    p = profile.get("personal_info", {})
    
    # Text Inputs
    inputs_map = {
        "#first_name": p.get("first_name", ""),
        "#last_name": p.get("last_name", ""),
        "#email": p.get("email", ""),
        "#phone": p.get("phone", ""),
    }

    for selector, value in inputs_map.items():
        if page.locator(selector).is_visible():
            page.fill(selector, value)

    # Custom question fields (e.g., LinkedIn, GitHub)
    page.evaluate("""({ linkedin, github }) => {
        const labels = Array.from(document.querySelectorAll('label'));
        labels.forEach(label => {
            const text = label.innerText.toLowerCase();
            const input = label.querySelector('input') || document.getElementById(label.getAttribute('for'));
            if (!input) return;
            if (text.includes('linkedin') && linkedin) input.value = linkedin;
            if (text.includes('github') && github) input.value = github;
        });
    }""", {"linkedin": p.get("linkedin", ""), "github": p.get("github", "")})

    # Resume Upload
    if pdf_path and os.path.exists(pdf_path):
        file_input = page.locator('input[type="file"][id*="resume"], input[type="file"][name*="resume"]')
        if file_input.count() > 0:
            file_input.first.set_input_files(pdf_path)


def fill_lever_form(page: Page, profile: dict, pdf_path: str):
    """Auto-fill Lever ATS form inputs."""
    p = profile.get("personal_info", {})

    inputs_map = {
        'input[name="name"]': f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
        'input[name="email"]': p.get("email", ""),
        'input[name="phone"]': p.get("phone", ""),
        'input[name="urls[LinkedIn]"]': p.get("linkedin", ""),
        'input[name="urls[GitHub]"]': p.get("github", ""),
    }

    for selector, value in inputs_map.items():
        try:
            if page.locator(selector).is_visible():
                page.fill(selector, value)
        except Exception:
            pass

    # Resume Upload
    if pdf_path and os.path.exists(pdf_path):
        file_input = page.locator('input[type="file"][name="resume"]')
        if file_input.count() > 0:
            file_input.first.set_input_files(pdf_path)


def fill_generic_form(page: Page, profile: dict, pdf_path: str):
    """Fallback auto-fill strategy for standard web application forms."""
    p = profile.get("personal_info", {})

    field_rules = [
        (['first_name', 'firstname', 'first-name', 'given-name'], p.get("first_name", "")),
        (['last_name', 'lastname', 'last-name', 'family-name'], p.get("last_name", "")),
        (['email', 'e-mail'], p.get("email", "")),
        (['phone', 'mobile', 'tel'], p.get("phone", "")),
        (['linkedin'], p.get("linkedin", "")),
        (['github'], p.get("github", ""))
    ]

    for keywords, value in field_rules:
        if not value:
            continue
        for kw in keywords:
            selector = f'input[name*="{kw}" i], input[id*="{kw}" i], input[autocomplete*="{kw}" i]'
            try:
                elem = page.locator(selector).first
                if elem.is_visible():
                    elem.fill(value)
                    break
            except Exception:
                pass

    # Generic file upload for resume
    if pdf_path and os.path.exists(pdf_path):
        try:
            file_inputs = page.locator('input[type="file"]')
            if file_inputs.count() > 0:
                file_inputs.first.set_input_files(pdf_path)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Auto-fill job application form using Playwright.")
    parser.add_argument("--url", required=True, help="Job Application URL")
    parser.add_argument("--profile", default="source_profile.json", help="Path to candidate profile JSON")
    parser.add_argument("--pdf", required=True, help="Path to compiled resume PDF")
    parser.add_argument("--auto-submit", action="store_true", help="Auto click submit after filling (default: false, HITL mode)")
    args = parser.parse_args()

    # Load candidate profile
    with open(args.profile, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    pdf_absolute_path = os.path.abspath(args.pdf)
    print(f"[PLAYWRIGHT] Navigating to: {args.url}")
    print(f"[PLAYWRIGHT] Using Resume PDF: {pdf_absolute_path}")

    with sync_playwright() as p:
        # Launch headful browser for Human-in-the-Loop observation & final click
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)

            url_lower = args.url.lower()

            if "greenhouse.io" in url_lower:
                print("[PLAYWRIGHT] Identified Greenhouse application form.")
                fill_greenhouse_form(page, profile_data, pdf_absolute_path)
            elif "lever.co" in url_lower:
                print("[PLAYWRIGHT] Identified Lever application form.")
                fill_lever_form(page, profile_data, pdf_absolute_path)
            else:
                print("[PLAYWRIGHT] Attempting generic application form filling...")
                fill_generic_form(page, profile_data, pdf_absolute_path)

            print("\n" + "="*60)
            print("HUMAN-IN-THE-LOOP (HITL) APPROVAL REQUIRED")
            print("Form fields have been filled and resume PDF uploaded.")
            print("Please review the browser window, complete any CAPTCHAs, and click Submit.")
            print("="*60 + "\n")

            if not args.auto_submit:
                input("Press ENTER in this terminal when you are done reviewing or submitting...")
            else:
                print("[PLAYWRIGHT] Auto-submit enabled. Attempting submission click...")
                submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
                if submit_btn.is_visible():
                    submit_btn.click()
                    time.sleep(3)

        except Exception as e:
            print(f"[PLAYWRIGHT ERROR] {e}", file=sys.stderr)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
