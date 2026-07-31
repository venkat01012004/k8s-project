# JobNest — Job Portal Web Application

A production-ready, full-stack Job Portal built with **Flask**, **MySQL**, **HTML/CSS/JavaScript**, containerized with **Docker**, and deployable to **Kubernetes** via a **GitHub Actions CI/CD pipeline**.

Two independent login modules — **Candidates** and **Recruiters** — share one clean, modern interface.

---

## Table of Contents

1. [Features](#features)
2. [Project Architecture](#project-architecture)
3. [Folder Structure](#folder-structure)
4. [Local Installation](#local-installation)
5. [MySQL Setup](#mysql-setup)
6. [Running the App](#running-the-app)
7. [Docker: Build & Run](#docker-build--run)
8. [Docker Hub: Push](#docker-hub-push)
9. [Kubernetes Deployment](#kubernetes-deployment)
10. [CI/CD Pipeline](#cicd-pipeline)
11. [Sample Login Credentials](#sample-login-credentials)
12. [Screenshots](#screenshots)
13. [Security Notes](#security-notes)

---

## Features

### Candidate Module
- Register / Login (secure password hashing via Werkzeug)
- Browse & search jobs (keyword, location, category, job type)
- View detailed job listings
- Apply for jobs with resume upload + cover letter
- View all applied jobs and their live status (Pending / Shortlisted / Accepted / Rejected)
- Update profile (skills, experience, education, resume, photo, LinkedIn)
- Logout

### Recruiter Module
- Register / Login
- Dashboard with hiring stats (jobs posted, open roles, total applicants)
- Post a new job
- Edit an existing job
- Delete a job
- View applicants per job (or across all jobs)
- Accept / reject / shortlist applications with one click
- Update company profile (logo, website, about company)
- Logout

### Platform
- Premium, responsive UI with a custom design system (navy/teal/coral palette, Space Grotesk + Inter typefaces)
- Animated hero, floating cards, scroll reveals, dashboard stat cards
- Secure sessions, input validation, and centralized error handling (`404`/`500` pages)
- Health-check endpoint (`/health`) for container/orchestrator probes
- Fully normalized MySQL schema with foreign keys and sample seed data

---

## Project Architecture

```
                     ┌───────────────────────┐
                     │        Browser        │
                     │ (HTML / CSS / JS)     │
                     └──────────┬────────────┘
                                │ HTTP
                     ┌──────────▼────────────┐
                     │   Flask Application    │
                     │  (app.py — routes,      │
                     │   auth, validation)     │
                     └──────────┬────────────┘
                                │ PyMySQL
                     ┌──────────▼────────────┐
                     │      MySQL Database    │
                     │  candidates, recruiters,│
                     │  jobs, applications     │
                     └────────────────────────┘

  Deployment flow:
  GitHub → GitHub Actions (build/test) → Docker Build → Docker Hub
        → Kubernetes Deployment → Service → Ingress → End Users
```

---

## Folder Structure

```
Job-Portal/
│
├── .github/workflows/ci-cd.yml     # CI/CD pipeline (build → push → deploy)
├── k8s/
│   ├── deployment.yaml             # Kubernetes Deployment (3 replicas, probes, secrets)
│   ├── service.yaml                # ClusterIP Service
│   └── ingress.yaml                # NGINX Ingress routing
├── static/
│   ├── css/style.css               # Design system + all component styles
│   ├── js/main.js                  # Nav, flash auto-dismiss, validation, reveals
│   ├── images/                     # Default avatar/logo illustrations (SVG)
│   └── uploads/                    # Resumes, photos, logos (runtime uploads)
├── templates/
│   ├── base.html                   # Shared layout: navbar, flash, footer
│   ├── index.html                  # Landing page
│   ├── login.html / register.html  # Auth pages (candidate + recruiter toggle)
│   ├── candidate-dashboard.html    # Candidate dashboard + applied jobs view
│   ├── recruiter-dashboard.html    # Recruiter dashboard
│   ├── jobs.html / job-details.html
│   ├── apply-job.html
│   ├── post-job.html               # Post + Edit job (shared)
│   ├── manage-jobs.html
│   ├── applicants.html
│   ├── profile.html                # Shared candidate/recruiter profile editor
│   └── error.html
├── app.py                          # Flask application (routes + business logic)
├── schema.sql                      # MySQL schema + sample seed data
├── Dockerfile
├── requirements.txt
├── .dockerignore
├── .gitignore
├── .env.example
└── README.md
```

---

## Local Installation

### Prerequisites
- Python 3.10+
- MySQL 8.0+ (or MariaDB 10.6+)
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/Job-Portal.git
cd Job-Portal

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment variables template
cp .env.example .env
# then edit .env with your DB credentials and a strong SECRET_KEY
```

---

## MySQL Setup

```bash
# 1. Log in to MySQL
mysql -u root -p

# 2. Run the schema file (creates database, tables, foreign keys, sample data)
source schema.sql;

# Or, from the shell, without logging in manually:
mysql -u root -p < schema.sql
```

This creates the `job_portal` database with four normalized tables:

| Table          | Purpose                                             |
|----------------|------------------------------------------------------|
| `recruiters`   | Company/recruiter accounts                           |
| `candidates`   | Candidate accounts and profile data                  |
| `jobs`         | Job postings (FK → `recruiters`)                     |
| `applications` | Job applications (FK → `jobs`, FK → `candidates`)    |

> **Note:** The sample seed data ships with placeholder password hashes. After loading the schema, either register fresh accounts through the UI, or regenerate real hashes:
> ```bash
> python3 -c "from werkzeug.security import generate_password_hash as g; print(g('Candidate@123'))"
> ```
> and `UPDATE` the relevant rows — or simply use the **Register** page, which is the recommended path.

---

## Running the App

```bash
# Development server
export FLASK_DEBUG=true      # Windows (PowerShell): $env:FLASK_DEBUG="true"
python3 app.py
```

Visit **http://localhost:5000**

For production-like local testing with Gunicorn:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
```

---

## Docker: Build & Run

```bash
# Build the image
docker build -t job-portal:latest .

# Run the container (connecting to a MySQL instance on the host)
docker run -d \
  --name job-portal \
  -p 5000:5000 \
  -e SECRET_KEY="your-production-secret" \
  -e DB_HOST="host.docker.internal" \
  -e DB_PORT="3306" \
  -e DB_USER="root" \
  -e DB_PASSWORD="root" \
  -e DB_NAME="job_portal" \
  job-portal:latest
```

Or with `docker-compose` alongside a MySQL container:

```yaml
# docker-compose.yml (optional, not included by default)
services:
  web:
    build: .
    ports: ["5000:5000"]
    environment:
      DB_HOST: db
      DB_USER: root
      DB_PASSWORD: root
      DB_NAME: job_portal
    depends_on: [db]
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: job_portal
    volumes:
      - ./schema.sql:/docker-entrypoint-initdb.d/schema.sql
```

---

## Docker Hub: Push

```bash
# 1. Log in to Docker Hub
docker login

# 2. Tag the image with your Docker Hub username
docker tag job-portal:latest <your-dockerhub-username>/job-portal:latest

# 3. Push it
docker push <your-dockerhub-username>/job-portal:latest
```

---

## Kubernetes Deployment

The `k8s/` folder contains three manifests: `deployment.yaml`, `service.yaml`, and `ingress.yaml`.

```bash
# 1. Create the secret referenced by deployment.yaml
kubectl create secret generic job-portal-secrets \
  --from-literal=SECRET_KEY='your-production-secret' \
  --from-literal=DB_HOST='mysql-service' \
  --from-literal=DB_PORT='3306' \
  --from-literal=DB_USER='root' \
  --from-literal=DB_PASSWORD='your-db-password' \
  --from-literal=DB_NAME='job_portal'

# 2. Update the image reference in k8s/deployment.yaml
#    <YOUR_DOCKERHUB_USERNAME>/job-portal:latest → your actual image

# 3. Apply the manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 4. Verify
kubectl get deployments
kubectl get pods
kubectl get svc job-portal-service
kubectl get ingress job-portal-ingress

# 5. Watch the rollout
kubectl rollout status deployment/job-portal-deployment
```

> The Ingress routes host `jobportal.local` to the service. Add an entry to `/etc/hosts` (or your DNS) pointing to your ingress controller's external IP for local testing.

---

## CI/CD Pipeline

`.github/workflows/ci-cd.yml` implements the full flow:

**GitHub push → Build & test → Docker build → Docker Hub push → Kubernetes deploy → Service → Ingress**

Required GitHub repository secrets:

| Secret               | Purpose                                       |
|-----------------------|------------------------------------------------|
| `DOCKERHUB_USERNAME`  | Docker Hub account username                    |
| `DOCKERHUB_TOKEN`     | Docker Hub access token                        |
| `KUBE_CONFIG_DATA`    | Base64-encoded kubeconfig for cluster access    |

---

## Sample Login Credentials

After loading `schema.sql` and registering fresh passwords (see [MySQL Setup](#mysql-setup)), sample accounts are:

**Recruiters** (`hr@technova.com`, `careers@brightedge.com`, `jobs@finserve.com`) — password: `Recruiter@123`
**Candidates** (`arjun.sharma@example.com`, `sneha.kapoor@example.com`, `karan.verma@example.com`) — password: `Candidate@123`

*(Passwords only work after you regenerate real hashes as described above — the shipped SQL file contains placeholders for security.)*

---

## Screenshots

> Add screenshots of your running application here once deployed:

| Page                  | Screenshot |
|-----------------------|------------|
| Landing Page          | `docs/screenshots/landing.png` |
| Job Search            | `docs/screenshots/jobs.png` |
| Candidate Dashboard   | `docs/screenshots/candidate-dashboard.png` |
| Recruiter Dashboard   | `docs/screenshots/recruiter-dashboard.png` |
| Post a Job            | `docs/screenshots/post-job.png` |
| Applicants View       | `docs/screenshots/applicants.png` |

---

## Security Notes

- Passwords are hashed with Werkzeug's `generate_password_hash` (scrypt-based), never stored in plaintext.
- Sessions are signed using Flask's `SECRET_KEY` — always set a strong, unique value in production via environment variables/secrets, never hardcode it.
- File uploads are restricted by extension and a 5 MB size limit; filenames are sanitized with `secure_filename`.
- All SQL queries use parameterized statements (`%s` placeholders) to prevent SQL injection.
- Role-based route protection ensures candidates and recruiters can only access their own data.
- Kubernetes secrets (`job-portal-secrets`) keep credentials out of manifests and version control.

---

Built with Flask, MySQL, and a lot of attention to detail. Happy hiring! 🚀
