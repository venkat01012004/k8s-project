"""
Job Portal - Flask Application
================================
A production-ready Job Portal web application supporting two user roles:
Candidates and Recruiters. Built with Flask + MySQL.

Author: Job Portal Team
"""

import os
import re
from datetime import datetime
from functools import wraps

import pymysql
import pymysql.cursors
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Load variables from a local .env file (if present) — no-op in production
# containers where env vars are injected directly (Docker/Kubernetes).
load_dotenv()

# ---------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max upload size

UPLOAD_FOLDER_RESUMES = os.path.join('static', 'uploads', 'resumes')
UPLOAD_FOLDER_PHOTOS = os.path.join('static', 'uploads', 'photos')
UPLOAD_FOLDER_LOGOS = os.path.join('static', 'uploads', 'logos')
ALLOWED_RESUME_EXT = {'pdf', 'doc', 'docx'}
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

for folder in (UPLOAD_FOLDER_RESUMES, UPLOAD_FOLDER_PHOTOS, UPLOAD_FOLDER_LOGOS):
    os.makedirs(folder, exist_ok=True)

# ---------------------------------------------------------------
# Database configuration (MySQL via PyMySQL)
# ---------------------------------------------------------------
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'root'),
    'database': os.environ.get('DB_NAME', 'job_portal'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': False,
}


def get_db():
    """Create and return a new MySQL database connection."""
    return pymysql.connect(**DB_CONFIG)


# ---------------------------------------------------------------
# Helper / utility functions
# ---------------------------------------------------------------

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email or '') is not None


def is_valid_password(password):
    """Password must be at least 6 characters."""
    return password and len(password) >= 6


def login_required(role=None):
    """Decorator to ensure a user is logged in, optionally enforcing role."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session or 'role' not in session:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('You are not authorized to view that page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_globals():
    """Make session data available in every template."""
    return dict(
        current_year=datetime.now().year,
        logged_in=('user_id' in session),
        user_role=session.get('role'),
        user_name=session.get('name'),
    )


# ---------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404,
                            message="The page you're looking for doesn't exist."), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500,
                            message="Something went wrong on our end. Please try again."), 500


@app.errorhandler(413)
def too_large(e):
    flash('File is too large. Maximum upload size is 5 MB.', 'danger')
    return redirect(request.referrer or url_for('index'))


# =================================================================
# PUBLIC ROUTES
# =================================================================

@app.route('/')
def index():
    """Landing page with featured jobs and stats."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT j.*, r.company_name, r.company_logo
                FROM jobs j JOIN recruiters r ON j.recruiter_id = r.recruiter_id
                WHERE j.status = 'Open'
                ORDER BY j.posted_at DESC LIMIT 6
            """)
            featured_jobs = cur.fetchall()

            cur.execute("SELECT COUNT(*) AS c FROM jobs WHERE status='Open'")
            total_jobs = cur.fetchone()['c']

            cur.execute("SELECT COUNT(*) AS c FROM recruiters")
            total_companies = cur.fetchone()['c']

            cur.execute("SELECT COUNT(*) AS c FROM candidates")
            total_candidates = cur.fetchone()['c']
    finally:
        db.close()

    return render_template('index.html',
                            featured_jobs=featured_jobs,
                            total_jobs=total_jobs,
                            total_companies=total_companies,
                            total_candidates=total_candidates)


@app.route('/jobs')
def jobs():
    """Browse / search all open jobs."""
    search = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()
    category = request.args.get('category', '').strip()
    job_type = request.args.get('job_type', '').strip()

    query = """
        SELECT j.*, r.company_name, r.company_logo
        FROM jobs j JOIN recruiters r ON j.recruiter_id = r.recruiter_id
        WHERE j.status = 'Open'
    """
    params = []

    if search:
        query += " AND (j.title LIKE %s OR j.description LIKE %s OR r.company_name LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if location:
        query += " AND j.location LIKE %s"
        params.append(f"%{location}%")
    if category:
        query += " AND j.category = %s"
        params.append(category)
    if job_type:
        query += " AND j.job_type = %s"
        params.append(job_type)

    query += " ORDER BY j.posted_at DESC"

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(query, params)
            job_list = cur.fetchall()
            cur.execute("SELECT DISTINCT category FROM jobs WHERE category IS NOT NULL")
            categories = [r['category'] for r in cur.fetchall()]
    finally:
        db.close()

    return render_template('jobs.html', jobs=job_list, categories=categories,
                            search=search, location=location,
                            category=category, job_type=job_type)


@app.route('/job/<int:job_id>')
def job_details(job_id):
    """Show details for a single job listing."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT j.*, r.company_name, r.company_logo, r.about_company, r.company_website
                FROM jobs j JOIN recruiters r ON j.recruiter_id = r.recruiter_id
                WHERE j.job_id = %s
            """, (job_id,))
            job = cur.fetchone()
            if not job:
                abort(404)

            already_applied = False
            if session.get('role') == 'candidate':
                cur.execute("""
                    SELECT application_id FROM applications
                    WHERE job_id=%s AND candidate_id=%s
                """, (job_id, session['user_id']))
                already_applied = cur.fetchone() is not None
    finally:
        db.close()

    return render_template('job-details.html', job=job, already_applied=already_applied)


# =================================================================
# AUTHENTICATION ROUTES
# =================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Unified registration page for both candidates & recruiters."""
    role = request.args.get('role', 'candidate')

    if request.method == 'POST':
        role = request.form.get('role', 'candidate')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # ---- Validation ----
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('register.html', role=role, form=request.form)
        if not is_valid_password(password):
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html', role=role, form=request.form)
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', role=role, form=request.form)

        db = get_db()
        try:
            with db.cursor() as cur:
                if role == 'candidate':
                    full_name = request.form.get('full_name', '').strip()
                    phone = request.form.get('phone', '').strip()
                    if not full_name:
                        flash('Full name is required.', 'danger')
                        return render_template('register.html', role=role, form=request.form)

                    cur.execute("SELECT candidate_id FROM candidates WHERE email=%s", (email,))
                    if cur.fetchone():
                        flash('An account with this email already exists.', 'danger')
                        return render_template('register.html', role=role, form=request.form)

                    hashed = generate_password_hash(password)
                    cur.execute("""
                        INSERT INTO candidates (full_name, email, password_hash, phone)
                        VALUES (%s, %s, %s, %s)
                    """, (full_name, email, hashed, phone))
                    db.commit()
                    flash('Registration successful! Please log in.', 'success')
                    return redirect(url_for('login', role='candidate'))

                else:  # recruiter
                    company_name = request.form.get('company_name', '').strip()
                    contact_person = request.form.get('contact_person', '').strip()
                    phone = request.form.get('phone', '').strip()
                    if not company_name or not contact_person:
                        flash('Company name and contact person are required.', 'danger')
                        return render_template('register.html', role=role, form=request.form)

                    cur.execute("SELECT recruiter_id FROM recruiters WHERE email=%s", (email,))
                    if cur.fetchone():
                        flash('An account with this email already exists.', 'danger')
                        return render_template('register.html', role=role, form=request.form)

                    hashed = generate_password_hash(password)
                    cur.execute("""
                        INSERT INTO recruiters (company_name, contact_person, email, password_hash, phone)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (company_name, contact_person, email, hashed, phone))
                    db.commit()
                    flash('Registration successful! Please log in.', 'success')
                    return redirect(url_for('login', role='recruiter'))
        except pymysql.MySQLError as e:
            db.rollback()
            flash(f'Database error: {str(e)}', 'danger')
        finally:
            db.close()

    return render_template('register.html', role=role, form={})


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login page for both candidates & recruiters."""
    role = request.args.get('role', 'candidate')

    if request.method == 'POST':
        role = request.form.get('role', 'candidate')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html', role=role)

        db = get_db()
        try:
            with db.cursor() as cur:
                if role == 'candidate':
                    cur.execute("SELECT * FROM candidates WHERE email=%s", (email,))
                    user = cur.fetchone()
                    id_field, name_field = 'candidate_id', 'full_name'
                else:
                    cur.execute("SELECT * FROM recruiters WHERE email=%s", (email,))
                    user = cur.fetchone()
                    id_field, name_field = 'recruiter_id', 'company_name'

                if user and check_password_hash(user['password_hash'], password):
                    session.clear()
                    session['user_id'] = user[id_field]
                    session['role'] = role
                    session['name'] = user[name_field]
                    session['email'] = user['email']
                    flash(f"Welcome back, {user[name_field]}!", 'success')
                    if role == 'candidate':
                        return redirect(url_for('candidate_dashboard'))
                    else:
                        return redirect(url_for('recruiter_dashboard'))
                else:
                    flash('Invalid email or password.', 'danger')
        finally:
            db.close()

    return render_template('login.html', role=role)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))


# =================================================================
# CANDIDATE ROUTES
# =================================================================

@app.route('/candidate/dashboard')
@login_required(role='candidate')
def candidate_dashboard():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT a.*, j.title, j.location, j.job_type, r.company_name, r.company_logo
                FROM applications a
                JOIN jobs j ON a.job_id = j.job_id
                JOIN recruiters r ON j.recruiter_id = r.recruiter_id
                WHERE a.candidate_id = %s
                ORDER BY a.applied_at DESC
            """, (session['user_id'],))
            applications = cur.fetchall()

            cur.execute("""
                SELECT j.*, r.company_name, r.company_logo
                FROM jobs j JOIN recruiters r ON j.recruiter_id = r.recruiter_id
                WHERE j.status='Open' ORDER BY j.posted_at DESC LIMIT 5
            """)
            recommended = cur.fetchall()

            stats = {
                'total': len(applications),
                'pending': sum(1 for a in applications if a['status'] == 'Pending'),
                'shortlisted': sum(1 for a in applications if a['status'] == 'Shortlisted'),
                'accepted': sum(1 for a in applications if a['status'] == 'Accepted'),
                'rejected': sum(1 for a in applications if a['status'] == 'Rejected'),
            }
    finally:
        db.close()

    return render_template('candidate-dashboard.html',
                            applications=applications, recommended=recommended, stats=stats)


@app.route('/candidate/applied-jobs')
@login_required(role='candidate')
def applied_jobs():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT a.*, j.title, j.location, j.job_type, j.salary_min, j.salary_max,
                       r.company_name, r.company_logo
                FROM applications a
                JOIN jobs j ON a.job_id = j.job_id
                JOIN recruiters r ON j.recruiter_id = r.recruiter_id
                WHERE a.candidate_id = %s
                ORDER BY a.applied_at DESC
            """, (session['user_id'],))
            applications = cur.fetchall()
    finally:
        db.close()
    return render_template('candidate-dashboard.html', applications=applications,
                            recommended=[], stats=None, applied_view=True)


@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
@login_required(role='candidate')
def apply_job(job_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT j.*, r.company_name FROM jobs j
                JOIN recruiters r ON j.recruiter_id = r.recruiter_id
                WHERE j.job_id=%s
            """, (job_id,))
            job = cur.fetchone()
            if not job:
                abort(404)
            if job['status'] != 'Open':
                flash('This job is no longer accepting applications.', 'warning')
                return redirect(url_for('job_details', job_id=job_id))

            cur.execute("SELECT * FROM applications WHERE job_id=%s AND candidate_id=%s",
                        (job_id, session['user_id']))
            if cur.fetchone():
                flash('You have already applied for this job.', 'info')
                return redirect(url_for('job_details', job_id=job_id))

            if request.method == 'POST':
                cover_letter = request.form.get('cover_letter', '').strip()
                resume_filename = None

                # handle uploaded resume (optional; falls back to profile resume)
                file = request.files.get('resume')
                if file and file.filename:
                    if not allowed_file(file.filename, ALLOWED_RESUME_EXT):
                        flash('Resume must be a PDF, DOC, or DOCX file.', 'danger')
                        return render_template('apply-job.html', job=job)
                    filename = secure_filename(f"resume_{session['user_id']}_{job_id}_{file.filename}")
                    file.save(os.path.join(UPLOAD_FOLDER_RESUMES, filename))
                    resume_filename = filename
                else:
                    cur.execute("SELECT resume_filename FROM candidates WHERE candidate_id=%s",
                                (session['user_id'],))
                    existing = cur.fetchone()
                    resume_filename = existing['resume_filename'] if existing else None

                if not resume_filename:
                    flash('Please upload a resume to apply.', 'danger')
                    return render_template('apply-job.html', job=job)

                cur.execute("""
                    INSERT INTO applications (job_id, candidate_id, cover_letter, resume_filename)
                    VALUES (%s, %s, %s, %s)
                """, (job_id, session['user_id'], cover_letter, resume_filename))
                db.commit()
                flash('Application submitted successfully!', 'success')
                return redirect(url_for('applied_jobs'))
    finally:
        db.close()

    return render_template('apply-job.html', job=job)


@app.route('/candidate/profile', methods=['GET', 'POST'])
@login_required(role='candidate')
def candidate_profile():
    db = get_db()
    try:
        with db.cursor() as cur:
            if request.method == 'POST':
                full_name = request.form.get('full_name', '').strip()
                phone = request.form.get('phone', '').strip()
                location = request.form.get('location', '').strip()
                headline = request.form.get('headline', '').strip()
                skills = request.form.get('skills', '').strip()
                experience_years = request.form.get('experience_years') or 0
                education = request.form.get('education', '').strip()
                linkedin_url = request.form.get('linkedin_url', '').strip()

                update_fields = """
                    full_name=%s, phone=%s, location=%s, headline=%s, skills=%s,
                    experience_years=%s, education=%s, linkedin_url=%s
                """
                params = [full_name, phone, location, headline, skills,
                          experience_years, education, linkedin_url]

                resume_file = request.files.get('resume')
                if resume_file and resume_file.filename:
                    if allowed_file(resume_file.filename, ALLOWED_RESUME_EXT):
                        filename = secure_filename(f"resume_{session['user_id']}_{resume_file.filename}")
                        resume_file.save(os.path.join(UPLOAD_FOLDER_RESUMES, filename))
                        update_fields += ", resume_filename=%s"
                        params.append(filename)
                    else:
                        flash('Resume must be PDF, DOC, or DOCX.', 'danger')

                photo_file = request.files.get('profile_photo')
                if photo_file and photo_file.filename:
                    if allowed_file(photo_file.filename, ALLOWED_IMAGE_EXT):
                        filename = secure_filename(f"photo_{session['user_id']}_{photo_file.filename}")
                        photo_file.save(os.path.join(UPLOAD_FOLDER_PHOTOS, filename))
                        update_fields += ", profile_photo=%s"
                        params.append(filename)
                    else:
                        flash('Profile photo must be an image file.', 'danger')

                params.append(session['user_id'])
                cur.execute(f"UPDATE candidates SET {update_fields} WHERE candidate_id=%s", params)
                db.commit()
                session['name'] = full_name
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('candidate_profile'))

            cur.execute("SELECT * FROM candidates WHERE candidate_id=%s", (session['user_id'],))
            candidate = cur.fetchone()
    finally:
        db.close()

    return render_template('profile.html', candidate=candidate, role='candidate')


# =================================================================
# RECRUITER ROUTES
# =================================================================

@app.route('/recruiter/dashboard')
@login_required(role='recruiter')
def recruiter_dashboard():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM jobs WHERE recruiter_id=%s ORDER BY posted_at DESC",
                        (session['user_id'],))
            my_jobs = cur.fetchall()

            cur.execute("""
                SELECT COUNT(*) AS c FROM applications a
                JOIN jobs j ON a.job_id=j.job_id WHERE j.recruiter_id=%s
            """, (session['user_id'],))
            total_applicants = cur.fetchone()['c']

            cur.execute("""
                SELECT COUNT(*) AS c FROM applications a
                JOIN jobs j ON a.job_id=j.job_id
                WHERE j.recruiter_id=%s AND a.status='Pending'
            """, (session['user_id'],))
            pending_review = cur.fetchone()['c']

            stats = {
                'total_jobs': len(my_jobs),
                'open_jobs': sum(1 for j in my_jobs if j['status'] == 'Open'),
                'total_applicants': total_applicants,
                'pending_review': pending_review,
            }
    finally:
        db.close()

    return render_template('recruiter-dashboard.html', jobs=my_jobs, stats=stats)


@app.route('/recruiter/post-job', methods=['GET', 'POST'])
@login_required(role='recruiter')
def post_job():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        category = request.form.get('category', '').strip()
        job_type = request.form.get('job_type', 'Full-Time')
        experience_level = request.form.get('experience_level', 'Entry Level')
        location = request.form.get('location', '').strip()
        salary_min = request.form.get('salary_min') or None
        salary_max = request.form.get('salary_max') or None
        vacancies = request.form.get('vacancies') or 1

        if not title or not description or not location:
            flash('Title, description, and location are required.', 'danger')
            return render_template('post-job.html', form=request.form)

        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute("""
                    INSERT INTO jobs (recruiter_id, title, description, requirements,
                        responsibilities, category, job_type, experience_level, location,
                        salary_min, salary_max, vacancies)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (session['user_id'], title, description, requirements, responsibilities,
                      category, job_type, experience_level, location, salary_min, salary_max, vacancies))
                db.commit()
                flash('Job posted successfully!', 'success')
                return redirect(url_for('manage_jobs'))
        finally:
            db.close()

    return render_template('post-job.html', form={})


@app.route('/recruiter/manage-jobs')
@login_required(role='recruiter')
def manage_jobs():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id=j.job_id) AS applicant_count
                FROM jobs j WHERE j.recruiter_id=%s ORDER BY j.posted_at DESC
            """, (session['user_id'],))
            my_jobs = cur.fetchall()
    finally:
        db.close()
    return render_template('manage-jobs.html', jobs=my_jobs)


@app.route('/recruiter/edit-job/<int:job_id>', methods=['GET', 'POST'])
@login_required(role='recruiter')
def edit_job(job_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM jobs WHERE job_id=%s AND recruiter_id=%s",
                        (job_id, session['user_id']))
            job = cur.fetchone()
            if not job:
                abort(404)

            if request.method == 'POST':
                title = request.form.get('title', '').strip()
                description = request.form.get('description', '').strip()
                requirements = request.form.get('requirements', '').strip()
                responsibilities = request.form.get('responsibilities', '').strip()
                category = request.form.get('category', '').strip()
                job_type = request.form.get('job_type', 'Full-Time')
                experience_level = request.form.get('experience_level', 'Entry Level')
                location = request.form.get('location', '').strip()
                salary_min = request.form.get('salary_min') or None
                salary_max = request.form.get('salary_max') or None
                vacancies = request.form.get('vacancies') or 1
                status = request.form.get('status', 'Open')

                cur.execute("""
                    UPDATE jobs SET title=%s, description=%s, requirements=%s,
                        responsibilities=%s, category=%s, job_type=%s, experience_level=%s,
                        location=%s, salary_min=%s, salary_max=%s, vacancies=%s, status=%s
                    WHERE job_id=%s AND recruiter_id=%s
                """, (title, description, requirements, responsibilities, category, job_type,
                      experience_level, location, salary_min, salary_max, vacancies, status,
                      job_id, session['user_id']))
                db.commit()
                flash('Job updated successfully!', 'success')
                return redirect(url_for('manage_jobs'))
    finally:
        db.close()

    return render_template('post-job.html', form=job, editing=True, job_id=job_id)


@app.route('/recruiter/delete-job/<int:job_id>', methods=['POST'])
@login_required(role='recruiter')
def delete_job(job_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE job_id=%s AND recruiter_id=%s",
                        (job_id, session['user_id']))
            db.commit()
            if cur.rowcount:
                flash('Job deleted successfully.', 'success')
            else:
                flash('Job not found or unauthorized.', 'danger')
    finally:
        db.close()
    return redirect(url_for('manage_jobs'))


@app.route('/recruiter/applicants')
@app.route('/recruiter/applicants/<int:job_id>')
@login_required(role='recruiter')
def applicants(job_id=None):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT job_id, title FROM jobs WHERE recruiter_id=%s ORDER BY posted_at DESC",
                        (session['user_id'],))
            my_jobs = cur.fetchall()

            query = """
                SELECT a.*, c.full_name, c.email, c.phone, c.location AS candidate_location,
                       c.skills, c.experience_years, c.profile_photo, j.title AS job_title
                FROM applications a
                JOIN candidates c ON a.candidate_id = c.candidate_id
                JOIN jobs j ON a.job_id = j.job_id
                WHERE j.recruiter_id = %s
            """
            params = [session['user_id']]
            if job_id:
                query += " AND a.job_id = %s"
                params.append(job_id)
            query += " ORDER BY a.applied_at DESC"

            cur.execute(query, params)
            applicant_list = cur.fetchall()
    finally:
        db.close()

    return render_template('applicants.html', applicants=applicant_list,
                            jobs=my_jobs, selected_job_id=job_id)


@app.route('/recruiter/application/<int:application_id>/status', methods=['POST'])
@login_required(role='recruiter')
def update_application_status(application_id):
    new_status = request.form.get('status')
    if new_status not in ('Pending', 'Shortlisted', 'Accepted', 'Rejected'):
        flash('Invalid status.', 'danger')
        return redirect(url_for('applicants'))

    db = get_db()
    try:
        with db.cursor() as cur:
            # ensure this application belongs to a job owned by the logged-in recruiter
            cur.execute("""
                UPDATE applications a
                JOIN jobs j ON a.job_id = j.job_id
                SET a.status = %s
                WHERE a.application_id = %s AND j.recruiter_id = %s
            """, (new_status, application_id, session['user_id']))
            db.commit()
            if cur.rowcount:
                flash(f'Application marked as {new_status}.', 'success')
            else:
                flash('Application not found or unauthorized.', 'danger')
    finally:
        db.close()
    return redirect(request.referrer or url_for('applicants'))


@app.route('/recruiter/profile', methods=['GET', 'POST'])
@login_required(role='recruiter')
def recruiter_profile():
    db = get_db()
    try:
        with db.cursor() as cur:
            if request.method == 'POST':
                company_name = request.form.get('company_name', '').strip()
                contact_person = request.form.get('contact_person', '').strip()
                phone = request.form.get('phone', '').strip()
                company_website = request.form.get('company_website', '').strip()
                industry = request.form.get('industry', '').strip()
                about_company = request.form.get('about_company', '').strip()

                update_fields = """
                    company_name=%s, contact_person=%s, phone=%s, company_website=%s,
                    industry=%s, about_company=%s
                """
                params = [company_name, contact_person, phone, company_website, industry, about_company]

                logo_file = request.files.get('company_logo')
                if logo_file and logo_file.filename:
                    if allowed_file(logo_file.filename, ALLOWED_IMAGE_EXT):
                        filename = secure_filename(f"logo_{session['user_id']}_{logo_file.filename}")
                        logo_file.save(os.path.join(UPLOAD_FOLDER_LOGOS, filename))
                        update_fields += ", company_logo=%s"
                        params.append(filename)
                    else:
                        flash('Logo must be an image file.', 'danger')

                params.append(session['user_id'])
                cur.execute(f"UPDATE recruiters SET {update_fields} WHERE recruiter_id=%s", params)
                db.commit()
                session['name'] = company_name
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('recruiter_profile'))

            cur.execute("SELECT * FROM recruiters WHERE recruiter_id=%s", (session['user_id'],))
            recruiter = cur.fetchone()
    finally:
        db.close()

    return render_template('profile.html', recruiter=recruiter, role='recruiter')


# =================================================================
# FILE SERVING (uploaded resumes / photos / logos)
# =================================================================

@app.route('/uploads/resumes/<filename>')
@login_required()
def serve_resume(filename):
    return send_from_directory(UPLOAD_FOLDER_RESUMES, filename)


@app.route('/uploads/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(UPLOAD_FOLDER_PHOTOS, filename)


@app.route('/uploads/logos/<filename>')
def serve_logo(filename):
    return send_from_directory(UPLOAD_FOLDER_LOGOS, filename)


# =================================================================
# HEALTH CHECK (used by Docker/Kubernetes probes)
# =================================================================
@app.route('/health')
def health_check():
    return jsonify(status='ok'), 200


# =================================================================
# MAIN ENTRY POINT
# =================================================================
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=debug_mode)
