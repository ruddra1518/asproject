import os
import uuid
import json
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

from azure.storage.blob import BlobServiceClient

from database import get_container_from_env

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "change-me")

# Azure Blob settings
AZURE_STORAGE_CONN = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "assignments")

# Cosmos container (uses COSMOS_ENDPOINT/COSMOS_KEY via database.py)
cosmos_container = get_container_from_env()

# Teacher credentials file (managed manually on the server)
TEACHERS_FILE = os.getenv("TEACHERS_FILE", "/etc/asproject/teachers.json")


def upload_file_to_blob(file_stream, filename, tracking_id: str) -> str:
    if not AZURE_STORAGE_CONN:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set")

    blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONN)
    container_client = blob_service.get_container_client(AZURE_STORAGE_CONTAINER)
    try:
        container_client.create_container()
    except Exception:
        # container may already exist
        pass

    blob_name = f"{tracking_id}/{secure_filename(filename)}"
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(file_stream, overwrite=True)
    return blob_client.url


def load_teachers():
    try:
        with open(TEACHERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def teacher_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("teacher"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    return redirect(url_for("home"))


@app.route("/home", methods=["GET"])
def home():
    return render_template("home.html")


@app.route("/student", methods=["GET"])
def student():
    return render_template("student.html")


@app.route("/submit", methods=["POST"])
def submit():
    try:
        name = request.form["name"].strip()
        erp = request.form["erp"].strip()
        branch = request.form["branch"].strip()
        section = request.form["section"].strip()
        subject = request.form["subject"].strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("file")

        if not (name and erp and branch and section and subject and file):
            flash("Please fill all required fields and attach the file.")
            return redirect(url_for("student"))

        tracking_id = uuid.uuid4().hex[:10]
        submitted_at = datetime.utcnow().isoformat()

        file_url = upload_file_to_blob(file.stream, file.filename, tracking_id)

        doc = {
            "id": tracking_id,
            "student_name": name,
            "erp": erp,
            "branch": branch,
            "section": section,
            "subject": subject,
            "description": description,
            "file_url": file_url,
            "submitted_at": submitted_at,
            "marks": None,
            "remark": None,
        }

        cosmos_container.upsert_item(doc)

        return render_template("student.html", success=True, tracking_id=tracking_id)
    except Exception as e:
        app.logger.exception("Submit error")
        flash(f"Error during submit: {e}")
        return redirect(url_for("student"))


@app.route("/teacher", methods=["GET"])
@teacher_required
def teacher():
    try:
        query = "SELECT * FROM c ORDER BY c.submitted_at DESC"
        items = list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))
        return render_template("teacher.html", items=items)
    except Exception as e:
        app.logger.exception("Teacher list error")
        flash(f"Error loading submissions: {e}")
        return render_template("teacher.html", items=[])


@app.route("/grade", methods=["POST"])
@teacher_required
def grade():
    try:
        tracking_id = request.form["tracking_id"].strip()
        marks = request.form.get("marks")
        remark = request.form.get("remark", "").strip()

        # find the item across partitions
        q = f"SELECT * FROM c WHERE c.id='{tracking_id}'"
        items = list(cosmos_container.query_items(query=q, enable_cross_partition_query=True))
        if not items:
            flash("Submission not found")
            return redirect(url_for("teacher"))

        item = items[0]
        item["marks"] = marks
        item["remark"] = remark
        item["graded_at"] = datetime.utcnow().isoformat()

        cosmos_container.upsert_item(item)
        flash("Grades updated")
        return redirect(url_for("teacher"))
    except Exception as e:
        app.logger.exception("Grade error")
        flash(f"Error updating grade: {e}")
        return redirect(url_for("teacher"))


@app.route("/track", methods=["GET", "POST"])
def track():
    result = None
    if request.method == "POST":
        tracking_id = request.form.get("tracking_id", "").strip()
        if tracking_id:
            q = f"SELECT * FROM c WHERE c.id='{tracking_id}'"
            items = list(cosmos_container.query_items(query=q, enable_cross_partition_query=True))
            result = items[0] if items else None
            if not result:
                flash("Tracking ID not found")

    return render_template("track.html", result=result)


@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("teacher")
    if request.method == "POST":
        teacher_id = request.form.get("teacher_id", "").strip()
        password = request.form.get("password", "")
        teachers = load_teachers()
        hashed = teachers.get(teacher_id)
        if hashed and check_password_hash(hashed, password):
            session["teacher"] = teacher_id
            flash("Logged in")
            return redirect(next_url)
        else:
            flash("Invalid teacher ID or password")

    return render_template("login.html", next=next_url)


@app.route("/logout")
def logout():
    session.pop("teacher", None)
    flash("Logged out")
    return redirect(url_for("student"))


if __name__ == "__main__":
    # Not for production — use a WSGI server + nginx
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=False)
