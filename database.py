import sqlite3
import os

DB = "database/examguard.db"


def get_db():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    os.makedirs("database", exist_ok=True)

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS candidates(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()