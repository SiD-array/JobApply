-- Migration 001: Initial Database Schema for JobApply
-- Up Migration: Creates enum types, core tables, relationships, and performance indexes.

BEGIN;

-- 1. ENUM TYPES
CREATE TYPE application_status AS ENUM (
    'Discovered',
    'Evaluated',
    'Approved',
    'Applied',
    'OA',
    'Interview',
    'Rejected',
    'Offer'
);

CREATE TYPE interview_probability AS ENUM (
    'High',
    'Medium',
    'Low'
);

-- 2. COMPANIES TABLE
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    website_url VARCHAR(512),
    logo_url VARCHAR(512),
    industry VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. JOBS TABLE
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    external_job_id VARCHAR(255),
    title VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    employment_type VARCHAR(64),
    experience_level VARCHAR(64),
    salary_range VARCHAR(128),
    description TEXT NOT NULL,
    apply_url VARCHAR(1024) NOT NULL UNIQUE,
    source VARCHAR(64) NOT NULL,
    posted_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. SKILLS TABLE & JOB_SKILLS MAPPING
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL UNIQUE,
    category VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE job_skills (
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

-- 5. RESUMES TABLE (Historical Tailored Resume Versions)
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    version INTEGER NOT NULL DEFAULT 1,
    profile_data JSONB NOT NULL,
    pdf_path VARCHAR(1024),
    ats_score INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. COVER_LETTERS TABLE (Historical Cover Letter Versions)
CREATE TABLE cover_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    markdown_content TEXT NOT NULL,
    pdf_path VARCHAR(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. EVALUATIONS TABLE (AI Evaluator History)
CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    decision VARCHAR(16) NOT NULL,
    interview_probability interview_probability NOT NULL,
    matched_role VARCHAR(255),
    matched_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    missing_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    strengths JSONB NOT NULL DEFAULT '[]'::jsonb,
    weaknesses JSONB NOT NULL DEFAULT '[]'::jsonb,
    reason TEXT NOT NULL,
    raw_eval_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. APPLICATIONS TABLE (Application Lifecycle Tracking)
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES resumes(id) ON DELETE SET NULL,
    cover_letter_id UUID REFERENCES cover_letters(id) ON DELETE SET NULL,
    evaluation_id UUID REFERENCES evaluations(id) ON DELETE SET NULL,
    status application_status NOT NULL DEFAULT 'Discovered',
    applied_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- PERFORMANCE INDEXES
CREATE INDEX idx_jobs_company_id ON jobs(company_id);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_evaluations_job_id ON evaluations(job_id);
CREATE INDEX idx_resumes_job_id ON resumes(job_id);
CREATE INDEX idx_cover_letters_job_id ON cover_letters(job_id);
CREATE INDEX idx_applications_status ON applications(status);

COMMIT;
