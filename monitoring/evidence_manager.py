from datetime import datetime
from database import get_db
import hashlib

def calculate_sha256(file_data):
    return hashlib.sha256(file_data).hexdigest()


def save_evidence(
    candidate_id,
    session_id,
    evidence_type,
    filename,
    mime_type,
    file_data,
    sha256_hash
):
    """
    Store examination evidence in the database.
    """

    connection = get_db()

    try:
        sha256_hash = calculate_sha256(file_data)
        created_at = datetime.now().isoformat()


        connection.execute("""
            INSERT INTO evidence
            (
                candidate_id,
                session_id,
                evidence_type,
                filename,
                mime_type,
                file_data,
                sha256_hash,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            session_id,
            evidence_type,
            filename,
            mime_type,
            file_data,
            sha256_hash,
            created_at
        ))

        connection.commit()

        print("================================")
        print("EVIDENCE SAVED")
        print("================================")
        print("Candidate ID :", candidate_id)
        print("Session ID   :", session_id)
        print("Evidence     :", evidence_type)
        print("Filename     :", filename)
        print("MIME Type    :", mime_type)
        print("Hash         :", sha256_hash)
        print("Created At   :", created_at)
        print("================================")

        return {"success": True,
                 "sha256_hash": sha256_hash}

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()



def get_evidence(evidence_id):

    connection = get_db()

    try:
        row=connection.execute("""
        select id, candidate_id, session_id, evidence_type, filename, mime_type, file_data, sha256_hash, created_at from evidence where id=?
        """,(evidence_id,)).fetchone()
        return row
    except Exception as e:
        print(f"Error retrieving evidence: {e}")
        raise
    finally:
        connection.close()

def verify_evidence(evidence_id):
    connection=get_db()
    try:
        row=connection.execute("""
        select file_data, sha256_hash from evidence where id=?
        """,(evidence_id,)).fetchone()

        if row is None:
            return {"success": False, 
                    "message": "Evidence not found."}

        storesd_hash=row["sha256_hash"]
        calculated_hash=calculate_sha256(row["file_data"])

        if storesd_hash==calculated_hash:
            return {"success": True, 
                    "message": "Evidence integrity verified."}
        else:
            return {"success": False, 
                    "message": "Evidence integrity compromised."}

    except Exception as e:
        print(f"Error verifying evidence: {e}")
        raise
    finally:
        connection.close()
    



# if __name__ == "__main__":

#     test_data = b"TEST SCREENSHOT DATA"

#     result = save_evidence(
#         candidate_id=1,
#         session_id="test-evidence-session",
#         evidence_type="screenshot",
#         filename="test_screenshot.jpg",
#         mime_type="image/jpeg",
#         file_data=test_data,
#         sha256_hash="test-hash"
#     )

#     print("Evidence result:", result)


# flow

# Screenshot
    # ↓
# JPEG/PNG bytes
    # ↓
# file_data
    # ↓
# SQLite BLOB

