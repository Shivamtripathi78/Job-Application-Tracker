from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, abort
)
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "careertrack-local-secret"

DATABASE = "applications.db"

STATUSES = [
    "Applied",
    "Under Review",
    "Interview",
    "Selected",
    "Rejected"
]


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            location TEXT,
            job_type TEXT,
            status TEXT NOT NULL DEFAULT 'Applied',
            application_date TEXT NOT NULL,
            job_link TEXT,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_application(application_id):
    conn = get_db()

    application = conn.execute(
        "SELECT * FROM applications WHERE id = ?",
        (application_id,)
    ).fetchone()

    conn.close()

    if application is None:
        abort(404)

    return application


def validate_application(form):
    company = form.get("company", "").strip()
    position = form.get("position", "").strip()
    status = form.get("status", "Applied").strip()
    application_date = form.get("application_date", "").strip()

    if not company or not position or not application_date:
        return "Company, position and application date are required."

    if len(company) > 100 or len(position) > 100:
        return "Company and position must be under 100 characters."

    if status not in STATUSES:
        return "Invalid application status."

    try:
        date.fromisoformat(application_date)
    except ValueError:
        return "Please enter a valid application date."

    return None


@app.route("/")
def index():

    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    if status_filter not in STATUSES:
        status_filter = ""

    conn = get_db()

    query = "SELECT * FROM applications WHERE 1=1"
    params = []

    if search:
        query += " AND (company LIKE ? OR position LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY application_date DESC, id DESC"

    applications = conn.execute(
        query, params
    ).fetchall()

    statistics = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Applied' THEN 1 ELSE 0 END) AS applied,
            SUM(CASE WHEN status = 'Under Review' THEN 1 ELSE 0 END) AS review,
            SUM(CASE WHEN status = 'Interview' THEN 1 ELSE 0 END) AS interviews,
            SUM(CASE WHEN status = 'Selected' THEN 1 ELSE 0 END) AS selected,
            SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) AS rejected
        FROM applications
    """).fetchone()

    conn.close()

    return render_template(
        "index.html",
        applications=applications,
        statistics=statistics,
        statuses=STATUSES,
        search=search,
        status_filter=status_filter
    )


@app.route("/add", methods=["GET", "POST"])
def add_application():

    if request.method == "POST":

        error = validate_application(request.form)

        if error:
            flash(error, "error")
            return render_template(
                "form.html",
                application=request.form,
                statuses=STATUSES,
                today=date.today().isoformat()
            )

        data = (
            request.form.get("company", "").strip(),
            request.form.get("position", "").strip(),
            request.form.get("location", "").strip(),
            request.form.get("job_type", "").strip(),
            request.form.get("status", "Applied").strip(),
            request.form.get("application_date", "").strip(),
            request.form.get("job_link", "").strip(),
            request.form.get("notes", "").strip()
        )

        conn = get_db()

        conn.execute("""
            INSERT INTO applications (
                company, position, location,
                job_type, status, application_date,
                job_link, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, data)

        conn.commit()
        conn.close()

        flash("Job application added successfully!", "success")

        return redirect(url_for("index"))

    return render_template(
        "form.html",
        application=None,
        statuses=STATUSES,
        today=date.today().isoformat()
    )


@app.route("/edit/<int:application_id>", methods=["GET", "POST"])
def edit_application(application_id):

    application = get_application(application_id)

    if request.method == "POST":

        error = validate_application(request.form)

        if error:
            flash(error, "error")
            return render_template(
                "form.html",
                application=request.form,
                statuses=STATUSES,
                today=date.today().isoformat()
            )

        data = (
            request.form.get("company", "").strip(),
            request.form.get("position", "").strip(),
            request.form.get("location", "").strip(),
            request.form.get("job_type", "").strip(),
            request.form.get("status", "Applied").strip(),
            request.form.get("application_date", "").strip(),
            request.form.get("job_link", "").strip(),
            request.form.get("notes", "").strip(),
            application_id
        )

        conn = get_db()

        conn.execute("""
            UPDATE applications
            SET company = ?,
                position = ?,
                location = ?,
                job_type = ?,
                status = ?,
                application_date = ?,
                job_link = ?,
                notes = ?
            WHERE id = ?
        """, data)

        conn.commit()
        conn.close()

        flash("Application updated successfully!", "success")

        return redirect(url_for("index"))

    return render_template(
        "form.html",
        application=application,
        statuses=STATUSES,
        today=date.today().isoformat()
    )


@app.route("/delete/<int:application_id>", methods=["POST"])
def delete_application(application_id):

    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM applications WHERE id = ?",
        (application_id,)
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        abort(404)

    flash("Application deleted successfully!", "success")

    return redirect(url_for("index"))


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)