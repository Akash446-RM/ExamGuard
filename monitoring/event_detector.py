"""
Rule-based suspicious event detection engine.

Watches browser activity and face-presence data as it is logged and
raises a row in `suspicious_events` whenever a candidate crosses one
of the configurable thresholds below.

Kept deliberately simple and transparent so invigilators can see
exactly why a flag was raised.
"""

from datetime import datetime, timedelta


# ------------------------------------------------------------
# CONFIGURABLE THRESHOLDS
# ------------------------------------------------------------

TAB_SWITCH_LIMIT = 3
FACE_ABSENT_SECONDS_LIMIT = 120
FOCUS_LOSS_LIMIT = 5
FOCUS_LOSS_WINDOW_SECONDS = 300


# ------------------------------------------------------------
# CHECK IF EVENT IS ALREADY FLAGGED
# ------------------------------------------------------------

def _already_flagged(connection, session_id, event_type):

    row = connection.execute("""
        SELECT id
        FROM suspicious_events
        WHERE session_id = ?
        AND event_type = ?
    """, (
        session_id,
        event_type
    )).fetchone()

    return row is not None


# ------------------------------------------------------------
# RAISE SUSPICIOUS EVENT
# ------------------------------------------------------------

def _raise_flag(
    connection,
    candidate_id,
    session_id,
    event_type,
    reason,
    severity
):

    # Avoid creating the same suspicious event multiple times
    if _already_flagged(
        connection,
        session_id,
        event_type
    ):
        return

    connection.execute("""
        INSERT INTO suspicious_events
            (
                candidate_id,
                session_id,
                event_type,
                reason,
                event_time,
                severity
            )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        candidate_id,
        session_id,
        event_type,
        reason,
        datetime.now().isoformat(),
        severity
    ))

    connection.commit()


# ------------------------------------------------------------
# RULE: EXCESSIVE TAB SWITCHING
# ------------------------------------------------------------

def check_tab_switches(
    connection,
    candidate_id,
    session_id
):

    count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'tab_switch'
    """, (
        session_id,
    )).fetchone()["total"]

    if count > TAB_SWITCH_LIMIT:

        _raise_flag(
            connection,
            candidate_id,
            session_id,
            "excessive_tab_switching",
            (
                f"Candidate switched away from the exam tab "
                f"{count} times, exceeding the allowed limit of "
                f"{TAB_SWITCH_LIMIT}."
            ),
            "High"
        )


# ------------------------------------------------------------
# RULE: EXCESSIVE FOCUS LOSS FREQUENCY
# ------------------------------------------------------------

def check_focus_loss_frequency(
    connection,
    candidate_id,
    session_id
):

    window_start = (
        datetime.now()
        - timedelta(
            seconds=FOCUS_LOSS_WINDOW_SECONDS
        )
    ).isoformat()

    count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'focus_lost'
        AND event_time >= ?
    """, (
        session_id,
        window_start
    )).fetchone()["total"]

    if count > FOCUS_LOSS_LIMIT:

        _raise_flag(
            connection,
            candidate_id,
            session_id,
            "excessive_focus_loss",
            (
                f"Candidate's browser window lost focus "
                f"{count} times within the last "
                f"{FOCUS_LOSS_WINDOW_SECONDS // 60} minutes, "
                f"exceeding the allowed limit of "
                f"{FOCUS_LOSS_LIMIT}."
            ),
            "Medium"
        )


# ------------------------------------------------------------
# RULE: FACE ABSENT FOR TOO LONG
# ------------------------------------------------------------

def check_face_absence(
    connection,
    candidate_id,
    session_id,
    ongoing_seconds
):

    if ongoing_seconds > FACE_ABSENT_SECONDS_LIMIT:

        _raise_flag(
            connection,
            candidate_id,
            session_id,
            "excessive_face_absence",
            (
                f"Candidate's face has been absent from the "
                f"camera for {int(ongoing_seconds)} seconds, "
                f"exceeding the "
                f"{FACE_ABSENT_SECONDS_LIMIT}-second limit."
            ),
            "High"
        )


# ------------------------------------------------------------
# ENTRY POINT
# Called from the browser-event route in app.py
# ------------------------------------------------------------

def evaluate_browser_event(
    connection,
    candidate_id,
    session_id,
    event_type
):

    if event_type == "tab_switch":

        check_tab_switches(
            connection,
            candidate_id,
            session_id
        )

    elif event_type == "focus_lost":

        check_focus_loss_frequency(
            connection,
            candidate_id,
            session_id
        )