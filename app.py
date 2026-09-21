from flask import Flask, request, render_template, session, redirect
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
from camera import capture_photo
from monitoring.face_logger import log_face_state
from monitoring.face_monitoring import detect_face
from monitoring import event_detector
from datetime import datetime

import os
import sqlite3
import uuid


# ----------------------------------------
# FLASK APPLICATION
# ----------------------------------------

app = Flask(__name__)

app.secret_key = "exam_guard_key"

upload_folder = "static/uploads"


# ----------------------------------------
# INITIALIZE DATABASE
# ----------------------------------------

init_db()


# ----------------------------------------
# HOME
# ----------------------------------------

@app.route("/")
def home():

    return "Welcome to Exam Guard"


# ----------------------------------------
# CAPTURE CANDIDATE PHOTO
# ----------------------------------------

@app.route("/capture-photo", methods=["POST"])
def captureCandidatePhoto():

    photo = request.files.get("photo")

    if not photo:

        return {
            "success": False,
            "message": "No photo uploaded"
        }, 400

    # Read uploaded image
    image_data = photo.read()

    # Process and save image
    photo_path = capture_photo(image_data)

    if not photo_path:

        return {
            "success": False,
            "message": "Could not process photo"
        }, 400

    # Temporarily store photo path
    # until registration is completed
    session["capture_photo"] = photo_path

    return {
        "success": True,
        "message": "Photo captured successfully",
        "photo_path": photo_path
    }, 200


# ----------------------------------------
# REGISTER
# ----------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # ----------------------------------------
        # VALIDATE REQUIRED FIELDS
        # ----------------------------------------

        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all required fields"
            )

        # ----------------------------------------
        # GET CAPTURED PHOTO
        # ----------------------------------------

        photo_path = session.get("capture_photo")

        if not photo_path:

            return render_template(
                "register.html",
                error="Please capture your photo before registering"
            )

        # ----------------------------------------
        # HASH PASSWORD
        # ----------------------------------------

        hashed_password = generate_password_hash(
            password
        )

        connection = get_db()

        try:

            # ----------------------------------------
            # INSERT CANDIDATE
            # ----------------------------------------

            connection.execute(
                """
                INSERT INTO candidates
                (
                    name,
                    email,
                    password,
                    photo
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    hashed_password,
                    photo_path
                )
            )

            connection.commit()

        except sqlite3.IntegrityError:

            # ----------------------------------------
            # DELETE PHOTO IF REGISTRATION FAILS
            # ----------------------------------------

            if os.path.exists(photo_path):

                os.remove(photo_path)

            session.pop(
                "capture_photo",
                None
            )

            return render_template(
                "register.html",
                error="Email already registered. Please use a different email."
            )

        finally:

            connection.close()

        # ----------------------------------------
        # REMOVE TEMPORARY PHOTO SESSION
        # ----------------------------------------

        session.pop(
            "capture_photo",
            None
        )

        return redirect("/login")

    return render_template(
        "register.html"
    )


# ----------------------------------------
# LOGIN
# ----------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db()

        try:

            # ----------------------------------------
            # FIND CANDIDATE
            # ----------------------------------------

            candidate = connection.execute(
                """
                SELECT *
                FROM candidates
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

        finally:

            connection.close()

        # ----------------------------------------
        # VERIFY PASSWORD
        # ----------------------------------------

        if candidate and check_password_hash(
            candidate["password"],
            password
        ):

            session["candidate_id"] = candidate["id"]

            return redirect("/dashboard")

        return "Invalid email or password"

    return render_template(
        "login.html"
    )


# ----------------------------------------
# DASHBOARD
# ----------------------------------------

@app.route("/dashboard")
def dashboard():

    if "candidate_id" not in session:

        return "Please login first"

    return render_template(
        "dashboard.html"
    )


# ----------------------------------------
# START EXAM
# ----------------------------------------

@app.route("/start-exam")
def start_exam():

    # ----------------------------------------
    # CHECK LOGIN
    # ----------------------------------------

    if "candidate_id" not in session:

        return {
            "success": False,
            "message": "Candidate is not logged in"
        }, 401

    candidate_id = session["candidate_id"]

    # ----------------------------------------
    # CREATE UNIQUE EXAM SESSION
    # ----------------------------------------

    exam_session_id = str(
        uuid.uuid4()
    )

    # ----------------------------------------
    # SAVE EXAM SESSION IN DATABASE
    # ----------------------------------------

    connection = get_db()

    try:

        connection.execute("""
            INSERT INTO exam_sessions
            (
                candidate_id,
                session_id,
                status,
                started_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            candidate_id,
            exam_session_id,
            "started",
            datetime.now().isoformat()
        ))

        connection.commit()

    except Exception as e:

        connection.rollback()

        return {
            "success": False,
            "message": str(e)
        }, 500

    finally:

        connection.close()

    # ----------------------------------------
    # STORE EXAM SESSION ID
    # ----------------------------------------

    session["exam_session_id"] = exam_session_id

    # ----------------------------------------
    # OPEN EXAM PAGE
    # ----------------------------------------

    return render_template(
        "exam.html"
    )

# ----------------------------------------
# MONITOR FACE
# ----------------------------------------

@app.route("/monitor-face", methods=["POST"])
def monitor_face():

    # ----------------------------------------
    # CHECK LOGIN
    # ----------------------------------------

    if "candidate_id" not in session:

        return {
            "success": False,
            "message": "Candidate is not logged in"
        }, 401

    candidate_id = session["candidate_id"]

    # ----------------------------------------
    # GET EXAM SESSION
    # ----------------------------------------

    exam_session_id = session.get(
        "exam_session_id"
    )

    if not exam_session_id:

        return {
            "success": False,
            "message": "Exam not started"
        }, 400

    # ----------------------------------------
    # GET IMAGE FROM BROWSER
    # ----------------------------------------

    image = request.files.get(
        "image"
    )

    if not image:

        return {
            "success": False,
            "message": "No image received"
        }, 400

    # ----------------------------------------
    # READ IMAGE
    # ----------------------------------------

    image_data = image.read()

    # ----------------------------------------
    # DETECT FACE
    # ----------------------------------------

    face_present, processed_image = detect_face(
        image_data
    )

    # ----------------------------------------
    # DETERMINE FACE STATE
    # ----------------------------------------

    if face_present:

        current_state = "face_detected"

    else:

        current_state = "face_absent"

    # ----------------------------------------
    # LOG FACE STATE
    # ----------------------------------------

    log_face_state(
        candidate_id,
        exam_session_id,
        current_state
    )

    # ----------------------------------------
    # RETURN RESULT
    # ----------------------------------------

    return {
        "success": True,
        "state": current_state
    }, 200


# ----------------------------------------
# LOG BROWSER EVENT
# ----------------------------------------

@app.route("/log-browser-event", methods=["POST"])
def log_browser_event():

    # ----------------------------------------
    # CHECK LOGIN
    # ----------------------------------------

    if "candidate_id" not in session:

        return {
            "success": False,
            "message": "Candidate is not logged in"
        }, 401

    candidate_id = session["candidate_id"]

    # ----------------------------------------
    # GET EXAM SESSION
    # ----------------------------------------

    exam_session_id = session.get(
        "exam_session_id"
    )

    if not exam_session_id:

        return {
            "success": False,
            "message": "Exam not started"
        }, 400

    # ----------------------------------------
    # GET JSON DATA
    # ----------------------------------------

    data = request.get_json()

    # IMPORTANT:
    # exam.html sends "event_type"
    # not "event"

    if not data or "event_type" not in data:

        return {
            "success": False,
            "message": "No event data received"
        }, 400

    event_type = data["event_type"]

    details = data.get(
        "details",
        ""
    )

    # ----------------------------------------
    # VALIDATE EVENT TYPE
    # ----------------------------------------

    if not event_type:

        return {
            "success": False,
            "message": "Event type is required"
        }, 400

    connection = get_db()

    try:

        # ----------------------------------------
        # INSERT BROWSER EVENT
        # ----------------------------------------

        connection.execute(
            """
            INSERT INTO browser_events
            (
                candidate_id,
                session_id,
                event_type,
                event_time,
                details
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                exam_session_id,
                event_type,
                datetime.now().isoformat(),
                details
            )
        )

        # ----------------------------------------
        # SAVE BROWSER EVENT
        # ----------------------------------------

        connection.commit()

        # ----------------------------------------
        # CHECK FOR SUSPICIOUS ACTIVITY
        # ----------------------------------------

        event_detector.evaluate_browser_event(
            connection,
            candidate_id,
            exam_session_id,
            event_type
        )

    except Exception as e:

        connection.rollback()

        return {
            "success": False,
            "message": str(e)
        }, 500

    finally:

        connection.close()

    # ----------------------------------------
    # RETURN SUCCESS
    # ----------------------------------------

    return {
        "success": True,
        "message": "Browser event saved"
    }, 200


# ----------------------------------------
# LOGOUT
# ----------------------------------------

@app.route("/logout")
def logout():

    # Clear login and exam session
    session.clear()

    return redirect(
        "/login"
    )


# ----------------------------------------
# RUN APPLICATION
# ----------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )