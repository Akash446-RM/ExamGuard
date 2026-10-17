import sqlite3
import os


DATABASE_DIR = "database"
DATABASE = os.path.join(DATABASE_DIR, "examguard.db")


# ============================================================
# DATABASE CONNECTION
# ============================================================
def get_db():

    # Make sure database folder exists
    os.makedirs(DATABASE_DIR, exist_ok=True)

    connection = sqlite3.connect(DATABASE)

    # Allows dictionary-style access:
    # candidate["id"]
    # candidate["name"]
    # candidate["email"]
    connection.row_factory = sqlite3.Row

    # Enable foreign key support
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================
def init_db():

    # Create database folder if it does not exist
    os.makedirs(DATABASE_DIR, exist_ok=True)

    connection = get_db()


    # ========================================================
    # 1. CANDIDATES TABLE
    # ========================================================
    connection.execute("""
        CREATE TABLE IF NOT EXISTS candidates (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            password TEXT NOT NULL,

            photo TEXT,

            created_at TEXT
        )
    """)


    # --------------------------------------------------------
    # CHECK CREATED_AT COLUMN
    # --------------------------------------------------------
    # Protects older existing databases.
    #
    # If created_at already exists:
    #     Nothing happens.
    #
    # If created_at does not exist:
    #     It will be added.
    # --------------------------------------------------------

    columns = connection.execute(
        "PRAGMA table_info(candidates)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    if "created_at" not in column_names:

        connection.execute("""
            ALTER TABLE candidates
            ADD COLUMN created_at TEXT
        """)


    # ========================================================
    # 2. FACE MONITORING EVENTS
    # ========================================================
    connection.execute("""
        CREATE TABLE IF NOT EXISTS face_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            candidate_id INTEGER NOT NULL,

            session_id TEXT NOT NULL,

            event_type TEXT NOT NULL,

            started_at TEXT NOT NULL,

            ended_at TEXT,

            duration_seconds REAL,

            FOREIGN KEY (candidate_id)
                REFERENCES candidates(id)
        )
    """)


    # ========================================================
    # 3. BROWSER ACTIVITY EVENTS
    # ========================================================
    connection.execute("""
        CREATE TABLE IF NOT EXISTS browser_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            candidate_id INTEGER NOT NULL,

            session_id TEXT NOT NULL,

            event_type TEXT NOT NULL,

            event_time TEXT NOT NULL,

            details TEXT,

            FOREIGN KEY (candidate_id)
                REFERENCES candidates(id)
        )
    """)


    # ========================================================
    # 4. SUSPICIOUS EVENTS
    # ========================================================
    connection.execute("""
        CREATE TABLE IF NOT EXISTS suspicious_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            candidate_id INTEGER NOT NULL,

            session_id TEXT NOT NULL,

            event_type TEXT NOT NULL,

            reason TEXT NOT NULL,

            event_time TEXT NOT NULL,

            severity TEXT NOT NULL,

            FOREIGN KEY (candidate_id)
                REFERENCES candidates(id)
        )
    """)


    # ========================================================
    # 5. EXAM SESSIONS
    # ========================================================
    connection.execute("""
        CREATE TABLE IF NOT EXISTS exam_sessions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            candidate_id INTEGER NOT NULL,

            session_id TEXT UNIQUE NOT NULL,

            status TEXT NOT NULL DEFAULT 'in_progress',

            started_at TEXT NOT NULL,

            paused_at TEXT,

            resumed_at TEXT,

            submitted_at TEXT,

            FOREIGN KEY (candidate_id)
                REFERENCES candidates(id)
        )
    """)


    # ========================================================
    # 6. INTEGRITY SCORES
    # ========================================================
    connection.execute("""
        CREATE TABLE IF NOT EXISTS integrity_scores (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            session_id TEXT UNIQUE NOT NULL,

            candidate_id INTEGER NOT NULL,

            event_penalty REAL NOT NULL,

            face_presence_ratio REAL NOT NULL,

            integrity_score REAL NOT NULL,

            risk_level TEXT NOT NULL,

            computed_at TEXT NOT NULL,

            FOREIGN KEY (candidate_id)
                REFERENCES candidates(id)
        )
    """)


    # ========================================================
    # 7. ALERTS
    # ========================================================
    # Used by alert_manager.py
    #
    # Stores alerts generated when suspicious/risky
    # activity is detected.
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS alerts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            candidate_id INTEGER NOT NULL,

            session_id TEXT NOT NULL,

            alert_type TEXT NOT NULL,

            severity TEXT NOT NULL,

            message TEXT NOT NULL,

            created_at TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'open',

            FOREIGN KEY (candidate_id)
                REFERENCES candidates(id)
        )
    """)


    # ========================================================
    # 8. INCIDENT LOGS
    # ========================================================
    # Used by incident_logger.py
    #
    # Stores suspicious incidents detected during an exam.
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS incident_logs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            candidate_id INTEGER NOT NULL,

            session_id TEXT NOT NULL,

            incident_type TEXT NOT NULL,

            severity TEXT NOT NULL,

            description TEXT NOT NULL,

            created_at TEXT NOT NULL,

            FOREIGN KEY (candidate_id)
                REFERENCES candidates(id)
        )
    """)


    # ========================================================
    # 9. EVIDENCE
    # ========================================================
    # Stores evidence associated with suspicious activity.
    #
    # Example:
    #   screenshot
    #   image
    #   browser evidence
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS evidence (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            candidate_id INTEGER NOT NULL,

            session_id TEXT NOT NULL,

            evidence_type TEXT NOT NULL,

            filename TEXT,

            mime_type TEXT NOT NULL,

            file_data BLOB NOT NULL,

            sha256_hash TEXT NOT NULL,

            created_at TEXT NOT NULL,

            FOREIGN KEY (candidate_id)
                REFERENCES candidates(id)
        )
    """)


    # ========================================================
    # SAVE DATABASE CHANGES
    # ========================================================

    connection.commit()


    # ========================================================
    # CLOSE DATABASE CONNECTION
    # ========================================================

    connection.close()




# ============================================================
# RUN DIRECTLY
# ============================================================
if __name__ == "__main__":

    init_db()

    print("======================================")
    print("ExamGuard Database Initialized")
    print("======================================")
    print(f"Database: {DATABASE}")