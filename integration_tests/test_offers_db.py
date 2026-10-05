from unittest.mock import MagicMock

from database.database import Database
from database.inserts import InsertDB
from offer import JobOffer


def create_test_tables(db: Database):
    with db._connect() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE Companies (
                id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                company TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE Offers (
                id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                salary_min DOUBLE PRECISION,
                salary_max DOUBLE PRECISION,
                date TEXT,
                source TEXT,
                salary_status TEXT,
                offer_status TEXT
            )
        """)


def test_save_same_offer_twice_creates_duplicate():
    db_connection = MagicMock()

    db_connection.__enter__.return_value = db_connection
    db_cursor = db_connection.cursor.return_value
    db_cursor.fetchone.side_effect = [(1,), (1,), (1,), (2,)]  # Mock the return values for save_company and save_offers

    db = Database()
    setattr(db, "_connect", MagicMock(return_value=db_connection))

    insert_db = InsertDB(db)

    offer = JobOffer(
        title="Analityk Danych",
        company="Datumo",
        location="Warsaw",
        salary_min=7000,
        salary_max=9000,
        date="2026-08-30",
        salary_status="offer",
    )

    first_id = insert_db.save_offers(offer, source="Pracuj.pl")
    second_id = insert_db.save_offers(offer, source="Pracuj.pl")

    assert first_id != second_id
