-- ============================================================
-- Job Portal - MySQL Database Schema
-- Normalized schema with foreign keys + sample seed data
-- ============================================================

CREATE DATABASE IF NOT EXISTS job_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE job_portal;

-- ------------------------------------------------------------
-- Table: recruiters
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recruiters (
    recruiter_id      INT AUTO_INCREMENT PRIMARY KEY,
    company_name      VARCHAR(150) NOT NULL,
    contact_person    VARCHAR(100) NOT NULL,
    email             VARCHAR(150) NOT NULL UNIQUE,
    password_hash     VARCHAR(255) NOT NULL,
    phone             VARCHAR(20),
    company_website   VARCHAR(255),
    company_logo      VARCHAR(255) DEFAULT 'default-company.png',
    industry          VARCHAR(100),
    about_company     TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: candidates
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id      INT AUTO_INCREMENT PRIMARY KEY,
    full_name         VARCHAR(100) NOT NULL,
    email             VARCHAR(150) NOT NULL UNIQUE,
    password_hash     VARCHAR(255) NOT NULL,
    phone             VARCHAR(20),
    location           VARCHAR(120),
    headline          VARCHAR(150),
    skills            TEXT,
    experience_years  DECIMAL(4,1) DEFAULT 0,
    education         VARCHAR(255),
    resume_filename   VARCHAR(255),
    profile_photo     VARCHAR(255) DEFAULT 'default-avatar.png',
    linkedin_url      VARCHAR(255),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: jobs
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    job_id            INT AUTO_INCREMENT PRIMARY KEY,
    recruiter_id      INT NOT NULL,
    title             VARCHAR(150) NOT NULL,
    description       TEXT NOT NULL,
    requirements      TEXT,
    responsibilities  TEXT,
    category          VARCHAR(100),
    job_type          ENUM('Full-Time','Part-Time','Internship','Contract','Remote') DEFAULT 'Full-Time',
    experience_level  ENUM('Entry Level','Mid Level','Senior Level','Manager') DEFAULT 'Entry Level',
    location          VARCHAR(120) NOT NULL,
    salary_min        INT,
    salary_max        INT,
    vacancies         INT DEFAULT 1,
    status            ENUM('Open','Closed') DEFAULT 'Open',
    posted_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (recruiter_id) REFERENCES recruiters(recruiter_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: applications
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS applications (
    application_id    INT AUTO_INCREMENT PRIMARY KEY,
    job_id            INT NOT NULL,
    candidate_id      INT NOT NULL,
    cover_letter      TEXT,
    resume_filename   VARCHAR(255),
    status            ENUM('Pending','Shortlisted','Accepted','Rejected') DEFAULT 'Pending',
    applied_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    UNIQUE KEY unique_application (job_id, candidate_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Indexes for faster search
-- ------------------------------------------------------------
CREATE INDEX idx_jobs_title ON jobs(title);
CREATE INDEX idx_jobs_location ON jobs(location);
CREATE INDEX idx_jobs_category ON jobs(category);
CREATE INDEX idx_applications_status ON applications(status);

-- ============================================================
-- SAMPLE SEED DATA
-- ============================================================

-- Recruiters (password for all sample recruiters is: Recruiter@123)
INSERT INTO recruiters (company_name, contact_person, email, password_hash, phone, company_website, company_logo, industry, about_company)
VALUES
('TechNova Solutions', 'Ananya Rao', 'hr@technova.com', 'pbkdf2:sha256:600000$placeholder$hash', '9876543210', 'https://technova.example.com', 'technova.png', 'Information Technology', 'TechNova Solutions builds cloud-native platforms for enterprises across the globe.'),
('BrightEdge Marketing', 'Rahul Mehta', 'careers@brightedge.com', 'pbkdf2:sha256:600000$placeholder$hash', '9123456780', 'https://brightedge.example.com', 'brightedge.png', 'Marketing & Advertising', 'BrightEdge Marketing crafts data-driven campaigns for high-growth brands.'),
('FinServe Bank', 'Priya Nair', 'jobs@finserve.com', 'pbkdf2:sha256:600000$placeholder$hash', '9988776655', 'https://finserve.example.com', 'finserve.png', 'Banking & Finance', 'FinServe Bank is a leading digital-first banking institution serving 2M+ customers.');

-- Candidates (password for all sample candidates is: Candidate@123)
INSERT INTO candidates (full_name, email, password_hash, phone, location, headline, skills, experience_years, education, profile_photo)
VALUES
('Arjun Sharma', 'arjun.sharma@example.com', 'pbkdf2:sha256:600000$placeholder$hash', '9000011111', 'Hyderabad, India', 'Full Stack Developer', 'Python, Flask, React, MySQL, Docker', 3.5, 'B.Tech in Computer Science', 'default-avatar.png'),
('Sneha Kapoor', 'sneha.kapoor@example.com', 'pbkdf2:sha256:600000$placeholder$hash', '9000022222', 'Bengaluru, India', 'Digital Marketing Specialist', 'SEO, SEM, Content Strategy, Analytics', 2.0, 'MBA in Marketing', 'default-avatar.png'),
('Karan Verma', 'karan.verma@example.com', 'pbkdf2:sha256:600000$placeholder$hash', '9000033333', 'Pune, India', 'Financial Analyst', 'Excel, Financial Modeling, SQL, Power BI', 4.0, 'M.Com Finance', 'default-avatar.png');

-- Jobs
INSERT INTO jobs (recruiter_id, title, description, requirements, responsibilities, category, job_type, experience_level, location, salary_min, salary_max, vacancies)
VALUES
(1, 'Python Backend Developer', 'We are looking for a skilled Python Backend Developer to build and maintain scalable web applications using Flask and MySQL.', 'Strong knowledge of Python, Flask, REST APIs, MySQL, Git.', 'Design APIs, optimize database queries, collaborate with frontend team, write unit tests.', 'Software Development', 'Full-Time', 'Mid Level', 'Hyderabad, India', 800000, 1400000, 2),
(1, 'Frontend Developer (React)', 'Join our product team to build delightful, responsive user interfaces using React and modern JavaScript.', 'Proficiency in React, JavaScript ES6+, HTML5, CSS3, responsive design.', 'Build UI components, collaborate with designers, ensure cross-browser compatibility.', 'Software Development', 'Full-Time', 'Entry Level', 'Bengaluru, India', 600000, 1000000, 3),
(1, 'DevOps Engineer', 'Manage CI/CD pipelines, container orchestration, and cloud infrastructure for our SaaS platform.', 'Experience with Docker, Kubernetes, AWS/GCP, Jenkins or GitHub Actions.', 'Automate deployments, monitor systems, ensure high availability.', 'Software Development', 'Full-Time', 'Senior Level', 'Remote', 1200000, 2000000, 1),
(2, 'Digital Marketing Executive', 'Plan and execute digital marketing campaigns across SEO, SEM, and social media channels.', 'Knowledge of Google Ads, SEO tools, content marketing, analytics.', 'Run campaigns, analyze performance, report insights to stakeholders.', 'Marketing', 'Full-Time', 'Entry Level', 'Mumbai, India', 400000, 700000, 4),
(2, 'Content Strategist', 'Own the content roadmap across blogs, social, and email for multiple client brands.', 'Excellent writing skills, SEO knowledge, content planning experience.', 'Plan editorial calendars, write and edit content, collaborate with design.', 'Marketing', 'Contract', 'Mid Level', 'Remote', 500000, 800000, 1),
(3, 'Financial Analyst', 'Support budgeting, forecasting, and financial reporting for the retail banking division.', 'Strong Excel and SQL skills, financial modeling experience, attention to detail.', 'Prepare reports, build models, support decision-making with data insights.', 'Finance', 'Full-Time', 'Mid Level', 'Pune, India', 700000, 1100000, 2),
(3, 'Risk Management Intern', 'Assist the risk team in identifying, assessing, and monitoring financial risks.', 'Pursuing/completed degree in Finance, Economics, or related field.', 'Support risk assessments, prepare documentation, assist senior analysts.', 'Finance', 'Internship', 'Entry Level', 'Mumbai, India', 200000, 300000, 3);
