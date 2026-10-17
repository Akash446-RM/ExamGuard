from database import get_db

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# GET SESSION DATA
# ============================================================

def get_session_data(candidate_id, session_id):

    connection = get_db()

    try:

        # ----------------------------------------------------
        # GET INTEGRITY SCORE
        # ----------------------------------------------------

        score = connection.execute(
            """
            SELECT
                integrity_score,
                risk_level,
                event_penalty,
                face_presence_ratio,
                computed_at
            FROM integrity_scores
            WHERE candidate_id = ?
            AND session_id = ?
            """,
            (
                candidate_id,
                session_id
            )
        ).fetchone()

        if score is None:

            raise ValueError(
                f"No integrity score found for "
                f"candidate_id={candidate_id}, "
                f"session_id={session_id}"
            )

        # ----------------------------------------------------
        # GET BROWSER EVENTS
        # ----------------------------------------------------

        events = connection.execute(
            """
            SELECT
                event_type,
                event_time,
                details
            FROM browser_events
            WHERE candidate_id = ?
            AND session_id = ?
            ORDER BY event_time
            """,
            (
                candidate_id,
                session_id
            )
        ).fetchall()

        # ----------------------------------------------------
        # GET FACE EVENTS
        # ----------------------------------------------------

        face_events = connection.execute(
            """
            SELECT
                event_type,
                started_at,
                ended_at,
                duration_seconds
            FROM face_events
            WHERE candidate_id = ?
            AND session_id = ?
            ORDER BY started_at
            """,
            (
                candidate_id,
                session_id
            )
        ).fetchall()

        # ----------------------------------------------------
        # RETURN SESSION DATA
        # ----------------------------------------------------

        return {
            "score": dict(score),

            "browser_events": [
                dict(event)
                for event in events
            ],

            "face_events": [
                dict(event)
                for event in face_events
            ]
        }

    finally:

        connection.close()


# ============================================================
# PREPARE REPORT CONTEXT
# ============================================================

def prepare_report_context(session_data):

    score = session_data["score"]

    browser_events = session_data["browser_events"]

    face_events = session_data["face_events"]

    report_context = {

        "integrity_score":
            score["integrity_score"],

        "risk_level":
            score["risk_level"],

        "event_penalty":
            score["event_penalty"],

        "face_presence_ratio":
            score["face_presence_ratio"],

        "computed_at":
            score["computed_at"],

        "browser_events":
            browser_events,

        "face_events":
            face_events
    }

    return report_context


# ============================================================
# CREATE REPORT PROMPT
# ============================================================

def create_report_prompt():

    prompt = ChatPromptTemplate.from_template(
        """
You are an examination integrity reporting assistant.

Your job is to analyze the provided examination
session data and generate an evidence-based report.

SESSION INFORMATION

Integrity Score:
{integrity_score}

Risk Level:
{risk_level}

Event Penalty:
{event_penalty}

Face Presence Ratio:
{face_presence_ratio}%

Report Computed At:
{computed_at}


BROWSER EVENTS

{browser_events}


FACE MONITORING EVENTS

{face_events}


REPORT REQUIREMENTS

1. Explain the integrity score.

2. Explain the risk level.

3. Summarize the face monitoring information.

4. Summarize the browser activity.

5. Mention important observed events.

6. Use only the information provided.

7. Do not invent events or values.

8. Do not change or recalculate the integrity score.

9. Do not claim that an event proves misconduct.

10. Treat the result as a review-support report.

Write the report in a clear and professional format.
"""
    )

    return prompt


# ============================================================
# TEST PROMPT
# ============================================================

def test_prompt():

    context = {

        "integrity_score": 85,

        "risk_level": "Low",

        "event_penalty": 15,

        "face_presence_ratio": 98,

        "computed_at":
            "2024-06-01 12:00:00",

        "browser_events": [

            {
                "event_type": "tab_switch",

                "event_time":
                    "2024-06-01 12:05:00",

                "details": None
            },

            {
                "event_type": "focus_lost",

                "event_time":
                    "2024-06-01 12:10:00",

                "details": None
            }
        ],

        "face_events": [

            {
                "event_type": "face_detected",

                "started_at":
                    "2024-06-01 12:00:00",

                "ended_at":
                    "2024-06-01 12:30:00",

                "duration_seconds": 1800
            }
        ]
    }

    prompt = create_report_prompt()

    messages = prompt.format_messages(
        **context
    )

    for message in messages:

        print(message.content)


# ============================================================
# CREATE LLM
# ============================================================

def create_llm():

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    return llm


# ============================================================
# TEST LLM
# ============================================================

def test_llm():

    llm = create_llm()

    response = llm.invoke(
        "You are an examination integrity reporting assistant."
    )

    print(
        "LLM Response:",
        response.content
    )


# ============================================================
# CREATE INTEGRITY REPORT CHAIN
# ============================================================

def create_integrity_report():

    prompt = create_report_prompt()

    llm = create_llm()

    chain = prompt | llm

    return chain


# ============================================================
# GENERATE REAL INTEGRITY REPORT
# ============================================================

def generate_real_integrity_report(
    candidate_id,
    session_id
):

    # --------------------------------------------------------
    # GET SESSION DATA
    # --------------------------------------------------------

    session_data = get_session_data(
        candidate_id,
        session_id
    )

    # --------------------------------------------------------
    # PREPARE CONTEXT
    # --------------------------------------------------------

    report_context = prepare_report_context(
        session_data
    )

    # --------------------------------------------------------
    # CREATE LLM CHAIN
    # --------------------------------------------------------

    chain = create_integrity_report()

    # --------------------------------------------------------
    # GENERATE REPORT
    # --------------------------------------------------------

    response = chain.invoke(
        report_context
    )

    report = response.content

    # --------------------------------------------------------
    # VALIDATE REPORT
    # --------------------------------------------------------

    validation = validate_ai_report(
        report,
        report_context
    )

    if not validation["valid"]:

        raise ValueError(
            f"AI report validation failed: "
            f"{validation['reason']}"
        )

    return report


# ============================================================
# VALIDATE AI REPORT
# ============================================================

def validate_ai_report(
    report,
    report_context
):

    # --------------------------------------------------------
    # CHECK EMPTY REPORT
    # --------------------------------------------------------

    if not report:

        return {
            "valid": False,
            "reason": "AI report is empty"
        }

    # --------------------------------------------------------
    # GET EXPECTED VALUES
    # --------------------------------------------------------

    integrity_score = str(
        report_context[
            "integrity_score"
        ]
    )

    risk_level = str(
        report_context[
            "risk_level"
        ]
    )

    # --------------------------------------------------------
    # CHECK INTEGRITY SCORE
    # --------------------------------------------------------

    if integrity_score not in report:

        return {
            "valid": False,
            "reason":
                "Integrity score missing from AI report"
        }

    # --------------------------------------------------------
    # CHECK RISK LEVEL
    # --------------------------------------------------------

    if risk_level.lower() not in report.lower():

        return {
            "valid": False,
            "reason":
                "Risk level missing from AI report"
        }

    # --------------------------------------------------------
    # FORBIDDEN PHRASES
    # --------------------------------------------------------

    forbidden_phrases = [

        "proved cheated",

        "proved misconduct",

        "definitely cheated",

        "candidate cheated"
    ]

    report_lower = report.lower()

    for phrase in forbidden_phrases:

        if phrase in report_lower:

            return {
                "valid": False,
                "reason":
                    f"Unsafe phrase found: {phrase}"
            }

    # --------------------------------------------------------
    # VALID REPORT
    # --------------------------------------------------------

    return {

        "valid": True,

        "reason":
            "AI report validation done"
    }


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # REAL SYNTHETIC TEST SESSION
    # --------------------------------------------------------

    candidate_id = 10

    session_id = (
        "8b895e48-ccd0-4c20-beed-13191dc64eca"
    )

    # --------------------------------------------------------
    # GENERATE REPORT
    # --------------------------------------------------------

    try:

        report = generate_real_integrity_report(
            candidate_id,
            session_id
        )

        print()

        print(
            "======================================"
        )

        print(
            "       EXAMGUARD INTEGRITY REPORT"
        )

        print(
            "======================================"
        )

        print()

        print(
            f"Candidate ID : {candidate_id}"
        )

        print(
            f"Session ID   : {session_id}"
        )

        print()

        print(report)

        print()

        print(
            "======================================"
        )

    except Exception as e:

        print()

        print(
            "ERROR GENERATING INTEGRITY REPORT"
        )

        print(
            "----------------------------------"
        )

        print(e)