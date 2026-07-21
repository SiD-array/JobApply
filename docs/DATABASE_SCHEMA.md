# 🗄️ PostgreSQL Database Schema Documentation

This document describes the relational database schema designed for **JobApply**. It tracks job listings, corporate profiles, historical AI evaluations, versioned tailored resumes, cover letters, and application lifecycle statuses (`Discovered` ➔ `Applied` ➔ `OA` ➔ `Interview` ➔ `Offer` / `Rejected`).

---

## 📐 Entity-Relationship Diagram (ERD)

```
                       +---------------+
                       |   COMPANIES   |
                       +---------------+
                               | 1
                               |
                               | N
+-----------------+    *   +---------------+   1       +------------------+
|     SKILLS      |--------|     JOBS      |-----------|   APPLICATIONS   |
+-----------------+        +---------------+           +------------------+
                               | 1     | 1                      | 1
                               |       |                        |
                               | N     | N                      |
                       +---------------+                        |
                       |  EVALUATIONS  |                        |
                       +---------------+                        v
                                                +-------------------------------+
                                                |  RESUMES  &  COVER_LETTERS    |
                                                +-------------------------------+
```

---

## 📑 Table Specifications

### 1. `companies`
Stores corporate profiles and hiring domain metadata.
- `id` (UUID, Primary Key)
- `name` (VARCHAR, Unique)
- `website_url` / `logo_url` / `industry`

### 2. `jobs`
Stores normalized job listings fetched across providers (LinkedIn, Greenhouse, Lever, Ashby, Workday, WellFound).
- `id` (UUID, Primary Key)
- `company_id` (UUID, Foreign Key ➔ `companies.id`)
- `title` / `location` / `employment_type` / `experience_level` / `salary_range`
- `description` (TEXT)
- `apply_url` (VARCHAR, Unique constraint)
- `source` (VARCHAR: `Greenhouse`, `Lever`, `LinkedIn`, etc.)

### 3. `skills` & `job_skills`
Stores technology catalog and many-to-many job skill associations.
- `skills`: `id`, `name`, `category`
- `job_skills`: `job_id`, `skill_id` (Composite Primary Key)

### 4. `evaluations`
Stores every AI Recruiter evaluation attempt with full LLM reasoning and score metrics.
- `id` (UUID, Primary Key)
- `job_id` (UUID, Foreign Key ➔ `jobs.id`)
- `score` (INTEGER 0-100)
- `interview_probability` (ENUM: `High`, `Medium`, `Low`)
- `matched_skills` / `missing_skills` / `strengths` / `weaknesses` (JSONB)
- `reason` (TEXT)
- `raw_eval_json` (JSONB)

### 5. `resumes`
Stores historical versions of candidate tailored resume profiles and compiled vector PDF file locations.
- `id` (UUID, Primary Key)
- `job_id` (UUID, Foreign Key ➔ `jobs.id`)
- `version` (INTEGER)
- `profile_data` (JSONB)
- `pdf_path` (VARCHAR)
- `ats_score` (INTEGER)

### 6. `cover_letters`
Stores versioned markdown cover letters and compiled PDF file locations.
- `id` (UUID, Primary Key)
- `job_id` (UUID, Foreign Key ➔ `jobs.id`)
- `markdown_content` (TEXT)
- `pdf_path` (VARCHAR)

### 7. `applications`
Tracks the active lifecycle status for every job.
- `id` (UUID, Primary Key)
- `job_id` (UUID, Foreign Key ➔ `jobs.id`, Unique)
- `status` (ENUM: `Discovered`, `Evaluated`, `Approved`, `Applied`, `OA`, `Interview`, `Rejected`, `Offer`)
- `applied_at` (TIMESTAMPTZ)
- `notes` (TEXT)

---

## ⚡ Running Migrations

### Apply Up Migration:
```bash
psql -h localhost -U postgres -d jobapply -f migrations/001_initial_schema.sql
```

### Rollback Down Migration:
```bash
psql -h localhost -U postgres -d jobapply -f migrations/001_initial_schema.down.sql
```
