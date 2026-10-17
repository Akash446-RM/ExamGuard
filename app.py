import sqlite3
import uuid
from datetime import datetime

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import init_db, get_db

# ============================================================
# EXISTING PROJECT MODULES
# ============================================================

# Your existing camera.py uses capture_photo()
from camera import capture_photo

# Your existing face monitoring module
from monitoring.face_monitoring import detect_face

from monitoring.face_logger import log_face_state

from monitoring import event_detector

from monitoring.integrity_score import compute_integrity_score

# New monitoring modules
from monitoring.incident_logger import create_incident
from monitoring.alert_manager import (
    create_alert,
    create_risk_alert
)

# AI integrity report
from ai.integrity_agent import generate_real_integrity_report


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.secret_key = "examguard-secret-key"


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if "candidate_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# ============================================================
# CAPTURE CANDIDATE PHOTO
# ============================================================

@app.route("/capture-photo", methods=["POST"])
def capture_candidate_photo():

    photo = request.files.get("photo")

    if not photo:

        return {
            "success": False,
            "message": "No photo uploaded"
        }, 400

    # --------------------------------------------------------
    # Read image
    # --------------------------------------------------------

    image_data = photo.read()

    # --------------------------------------------------------
    # IMPORTANT:
    # Use existing camera.py function
    # --------------------------------------------------------

    photo_path = capture_photo(image_data)

    if not photo_path:

        return {
            "success": False,
            "message": "Could not process photo"
        }, 400

    # --------------------------------------------------------
    # Store photo temporarily
    # --------------------------------------------------------

    session["capture_photo"] = photo_path

    return {
        "success": True,
        "message": "Photo captured successfully",
        "photo_path": photo_path
    }, 200


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # ----------------------------------------------------
        # Validate fields
        # ----------------------------------------------------

        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in every field."
            )

        # ----------------------------------------------------
        # Get captured photo
        # ----------------------------------------------------

        photo_path = session.get(
            "capture_photo"
        )

        if not photo_path:

            return render_template(
                "register.html",
                error="Please capture your photo before registering."
            )

        # ----------------------------------------------------
        # Hash password
        # ----------------------------------------------------

        hashed_password = generate_password_hash(
            password
        )

        connection = get_db()

        try:

            connection.execute("""
                INSERT INTO candidates
                (
                    name,
                    email,
                    password,
                    photo
                )
                VALUES (?, ?, ?, ?)
            """, (
                name,
                email,
                hashed_password,
                photo_path
            ))

            connection.commit()

            # Remove temporary photo session
            session.pop(
                "capture_photo",
                None
            )

            return redirect(
                url_for(
                    "login",
                    registered=1
                )
            )

        except sqlite3.IntegrityError:

            connection.rollback()

            return render_template(
                "register.html",
                error="An account with this email already exists."
            )

        except Exception as e:

            connection.rollback()

            return render_template(
                "register.html",
                error=f"Registration failed: {e}"
            )

        finally:

            connection.close()

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db()

        try:

            candidate = connection.execute("""
                SELECT *
                FROM candidates
                WHERE email = ?
            """, (
                email,
            )).fetchone()

            # ------------------------------------------------
            # Check credentials
            # ------------------------------------------------

            if (
                candidate
                and check_password_hash(
                    candidate["password"],
                    password
                )
            ):

                session["candidate_id"] = candidate["id"]

                session["candidate_name"] = candidate["name"]

                return redirect(
                    url_for("dashboard")
                )

            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        finally:

            connection.close()

    registered = request.args.get(
        "registered"
    )

    return render_template(
        "login.html",
        registered=registered
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    candidate_id = session["candidate_id"]

    connection = get_db()

    try:

        # ----------------------------------------------------
        # Get candidate
        # ----------------------------------------------------

        candidate = connection.execute("""
            SELECT *
            FROM candidates
            WHERE id = ?
        """, (
            candidate_id,
        )).fetchone()

        if not candidate:

            session.clear()

            return redirect(
                url_for("login")
            )

        # ----------------------------------------------------
        # Get recent exam sessions
        # ----------------------------------------------------

        recent_sessions = connection.execute("""
            SELECT
                session_id,
                status,
                started_at,
                submitted_at
            FROM exam_sessions
            WHERE candidate_id = ?
            ORDER BY started_at DESC
            LIMIT 5
        """, (
            candidate_id,
        )).fetchall()

        return render_template(
            "dashboard.html",
            candidate=candidate,
            recent_sessions=recent_sessions
        )

    finally:

        connection.close()


# ============================================================
# START EXAM
# ============================================================

@app.route("/start-exam")
def start_exam():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    candidate_id = session["candidate_id"]

    # --------------------------------------------------------
    # Generate unique exam session ID
    # --------------------------------------------------------

    exam_session_id = str(
        uuid.uuid4()
    )

    # --------------------------------------------------------
    # Save in Flask session
    # --------------------------------------------------------

    session["exam_session_id"] = exam_session_id

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
            "in_progress",
            datetime.now().isoformat()
        ))

        connection.commit()

    except Exception as e:

        connection.rollback()

        session.pop(
            "exam_session_id",
            None
        )

        return f"Could not start exam: {e}", 500

    finally:

        connection.close()

    return render_template(
        "exam.html",
        candidate_name=session.get(
            "candidate_name"
        )
    )


# ============================================================
# PAUSE EXAM
# ============================================================

@app.route("/pause-exam", methods=["POST"])
def pause_exam():

    if (
        "candidate_id" not in session
        or "exam_session_id" not in session
    ):

        return {
            "success": False,
            "message": "No active exam session"
        }, 400

    connection = get_db()

    try:

        connection.execute("""
            UPDATE exam_sessions

            SET
                status = 'paused',
                paused_at = ?

            WHERE
                session_id = ?
                AND candidate_id = ?
        """, (
            datetime.now().isoformat(),
            session["exam_session_id"],
            session["candidate_id"]
        ))

        connection.commit()

    finally:

        connection.close()

    return {
        "success": True,
        "message": "Exam paused"
    }


# ============================================================
# RESUME EXAM
# ============================================================

@app.route("/resume-exam", methods=["POST"])
def resume_exam():

    if (
        "candidate_id" not in session
        or "exam_session_id" not in session
    ):

        return {
            "success": False,
            "message": "No active exam session"
        }, 400

    connection = get_db()

    try:

        connection.execute("""
            UPDATE exam_sessions

            SET
                status = 'in_progress',
                resumed_at = ?

            WHERE
                session_id = ?
                AND candidate_id = ?
        """, (
            datetime.now().isoformat(),
            session["exam_session_id"],
            session["candidate_id"]
        ))

        connection.commit()

    finally:

        connection.close()

    return {
        "success": True,
        "message": "Exam resumed"
    }


# ============================================================
# FACE MONITORING
# ============================================================

@app.route("/monitor-face", methods=["POST"])
def monitor_face():

    # --------------------------------------------------------
    # Check login
    # --------------------------------------------------------

    if "candidate_id" not in session:

        return {
            "success": False,
            "message": "Candidate is not logged in"
        }, 401

    candidate_id = session["candidate_id"]

    # --------------------------------------------------------
    # Get exam session
    # --------------------------------------------------------

    exam_session_id = session.get(
        "exam_session_id"
    )

    if not exam_session_id:

        return {
            "success": False,
            "message": "Exam not started"
        }, 400

    # --------------------------------------------------------
    # IMPORTANT:
    # Your existing face-monitoring frontend/module
    # uses "image"
    # --------------------------------------------------------

    image = request.files.get(
        "image"
    )

    if not image:

        # Also accept "frame" if the newer frontend sends it
        image = request.files.get(
            "frame"
        )

    if not image:

        return {
            "success": False,
            "message": "No image received"
        }, 400

    # --------------------------------------------------------
    # Read image
    # --------------------------------------------------------

    image_data = image.read()

    # --------------------------------------------------------
    # IMPORTANT:
    # Your existing detect_face() returns:
    #
    # face_present, processed_image
    # --------------------------------------------------------

    face_present, processed_image = detect_face(
        image_data
    )

    # --------------------------------------------------------
    # Determine face state
    # --------------------------------------------------------

    if face_present:

        current_state = "face_detected"

    else:

        current_state = "face_absent"

    # --------------------------------------------------------
    # Log face state
    # --------------------------------------------------------

    log_face_state(
        candidate_id,
        exam_session_id,
        current_state
    )

    return {
        "success": True,
        "state": current_state
    }, 200


# ============================================================
# BROWSER EVENT LOGGING
# ============================================================

@app.route("/log-browser-event", methods=["POST"])
def log_browser_event():

    # --------------------------------------------------------
    # Check login
    # --------------------------------------------------------

    if "candidate_id" not in session:

        return {
            "success": False,
            "message": "Candidate is not logged in"
        }, 401

    candidate_id = session["candidate_id"]

    # --------------------------------------------------------
    # Get exam session
    # --------------------------------------------------------

    exam_session_id = session.get(
        "exam_session_id"
    )

    if not exam_session_id:

        return {
            "success": False,
            "message": "Exam not started"
        }, 400

    # --------------------------------------------------------
    # Read JSON
    # --------------------------------------------------------

    data = request.get_json(
        silent=True
    )

    if not data:

        return {
            "success": False,
            "message": "No event data received"
        }, 400

    event_type = data.get(
        "event_type"
    )

    details = data.get(
        "details",
        ""
    )

    if not event_type:

        return {
            "success": False,
            "message": "Event type is required"
        }, 400

    connection = get_db()

    try:

        # ----------------------------------------------------
        # Save browser event
        # ----------------------------------------------------

        connection.execute("""
            INSERT INTO browser_events
            (
                candidate_id,
                session_id,
                event_type,
                event_time,
                details
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            candidate_id,
            exam_session_id,
            event_type,
            datetime.now().isoformat(),
            details
        ))

        connection.commit()

        print(
            "================================"
        )

        print(
            "BROWSER EVENT RECEIVED"
        )

        print(
            "Candidate ID:",
            candidate_id
        )

        print(
            "Session ID:",
            exam_session_id
        )

        print(
            "Event:",
            event_type
        )

        print(
            "Details:",
            details
        )

        print(
            "================================"
        )

        # ----------------------------------------------------
        # Run rule-based event detector
        # ----------------------------------------------------

        rule_results = (
            event_detector.evaluate_browser_event(
                connection,
                candidate_id,
                exam_session_id,
                event_type
            )
        )

        print(
            "Rule Results:",
            rule_results
        )

        # ----------------------------------------------------
        # Create incident and alert if suspicious
        # ----------------------------------------------------

        if rule_results:

            create_incident(
                candidate_id=candidate_id,
                session_id=exam_session_id,
                event_type=rule_results["event_type"],
                description=rule_results["description"],
                severity=rule_results["severity"]
            )

            create_alert(
                candidate_id=candidate_id,
                session_id=exam_session_id,
                alert_type=rule_results["event_type"],
                message=rule_results["description"],
                severity=rule_results["severity"]
            )

    except Exception as e:

        connection.rollback()

        print(
            "BROWSER EVENT ERROR:",
            e
        )

        return {
            "success": False,
            "message": str(e)
        }, 500

    finally:

        connection.close()

    return {
        "success": True,
        "message": "Browser event saved"
    }


# ============================================================
# SUBMIT EXAM
# ============================================================

@app.route("/submit-exam", methods=["POST"])
def submit_exam():

    # --------------------------------------------------------
    # Check candidate and exam session
    # --------------------------------------------------------

    if (
        "candidate_id" not in session
        or "exam_session_id" not in session
    ):

        return {
            "success": False,
            "message": "No active exam session"
        }, 400

    candidate_id = session["candidate_id"]

    exam_session_id = session["exam_session_id"]

    submitted_at = datetime.now().isoformat()

    # --------------------------------------------------------
    # Update exam session
    # --------------------------------------------------------

    connection = get_db()

    try:

        connection.execute("""
            UPDATE exam_sessions

            SET
                status = 'submitted',
                submitted_at = ?

            WHERE
                session_id = ?
                AND candidate_id = ?
        """, (
            submitted_at,
            exam_session_id,
            candidate_id
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

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # We DO NOT call close_open_face_event()
    # because your existing face_monitoring.py does not
    # contain that function.
    #
    # face_logger.py already manages face state transitions.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # Calculate integrity score
    # --------------------------------------------------------

    try:

        result = compute_integrity_score(
            candidate_id,
            exam_session_id
        )

    except Exception as e:

        return {
            "success": False,
            "message":
                f"Integrity score calculation failed: {e}"
        }, 500

    # --------------------------------------------------------
    # Create risk alert
    # --------------------------------------------------------

    try:

        create_risk_alert(
            candidate_id=candidate_id,
            session_id=exam_session_id,
            risk_level=result["risk_level"],
            integrity_score=result["integrity_score"]
        )

    except Exception as e:

        # Alert failure should not prevent
        # exam submission

        print(
            "RISK ALERT ERROR:",
            e
        )

    # --------------------------------------------------------
    # Generate AI integrity report
    #
    # This is intentionally non-blocking.
    #
    # If OpenAI quota/API fails, the exam still submits.
    # --------------------------------------------------------

    report = None

    try:

        report = generate_real_integrity_report(
            candidate_id,
            exam_session_id
        )

        print(
            "================================"
        )

        print(
            "AI-GENERATED INTEGRITY REPORT"
        )

        print(
            report
        )

        print(
            "================================"
        )

    except Exception as e:

        print(
            "AI REPORT GENERATION FAILED:"
        )

        print(
            e
        )

    # --------------------------------------------------------
    # Remove active exam session
    # --------------------------------------------------------

    session.pop(
        "exam_session_id",
        None
    )

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "success": True,

        "message":
            "Exam submitted successfully",

        "integrity_score":
            result["integrity_score"],

        "face_presence_ratio":
            result["face_presence_ratio"],

        "event_penalty":
            result["event_penalty"],

        "risk_level":
            result["risk_level"],

        "redirect":
            url_for("dashboard")
    }


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# RUN APPLICATION
# ============================================================


if __name__ == "__main__":

    app.run(
        debug=True
    )