import sqlite3

from modules.db_save import Database
from offer import JobOffer


def create_test_tables(db_name: str):
    with sqlite3.connect(db_name) as conn:
        conn.execute("""
            CREATE TABLE Companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT UNIQUE NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE Offers(
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                title TEXT, 
                company TEXT, 
                location TEXT, 
                salary_min REAL, 
                salary_max REAL, 
                date TEXT, 
                source TEXT, 
                salary_status TEXT
                )
            """)


def test_save_same_offer_twice_creates_duplicate(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(str(db_path))

    create_test_tables(str(db_path))

    offer = JobOffer(
        title="Analityk Danych",
        company="Datumo",
        location="Warsaw",
        salary_min=7000,
        salary_max=9000,
        date="2026-08-30",
        salary_status="offer",
    )

    first_id = db.save_offers(offer, source="Pracuj.pl")
    second_id = db.save_offers(offer, source="Pracuj.pl")

    assert first_id != second_id
