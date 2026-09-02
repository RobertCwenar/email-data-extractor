import sqlite3

from modules.db_save import Database
from offer import JobContract, JobOffer


def create_test_offer_db(db_name: str):
    with sqlite3.connect(db_name) as conn:
        conn.execute("""
            CREATE TABLE Companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT UNIQUE NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE Offers (
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

        conn.execute("""
            CREATE TABLE JobContracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                contract_type TEXT,
                salary_currency TEXT,
                salary_period TEXT,
                salary_min_offer REAL,
                salary_max_offer REAL,
                salary_min_monthly REAL,
                salary_max_monthly REAL
            )
        """)


def test_save_offer_with_uop_and_b2b(tmp_path):
    db_path = str(tmp_path / "test.db")

    create_test_offer_db(db_path)

    db = Database(db_path)

    offer = JobOffer(
        title="Analityk Danych",
        company="Datumo",
        location="Wrocław",
        salary_min=7000,
        salary_max=9000,
        date="2026-08-30",
        salary_status="offer",
    )

    offer_id = db.save_offers(
        offer,
        source="Pracuj.pl",
    )

    contracts = [
        JobContract(
            offer_id=offer_id,
            contract_type="UoP",
            salary_currency="PLN",
            salary_period="monthly",
            salary_min_offer=7000,
            salary_max_offer=9000,
            salary_min_monthly=7000,
            salary_max_monthly=9000,
        ),
        JobContract(
            offer_id=offer_id,
            contract_type="B2B",
            salary_currency="PLN",
            salary_period="hourly",
            salary_min_offer=35,
            salary_max_offer=45,
            salary_min_monthly=5880,
            salary_max_monthly=7560,
        ),
    ]

    for contract in contracts:
        db.save_job_contract(contract)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT contract_type, salary_period,
                   salary_min_offer, salary_max_offer
            FROM JobContracts
            WHERE offer_id = ?
        """,
            (offer_id,),
        ).fetchall()

    assert len(rows) == 2

    assert rows[0][0] == "UoP"
    assert rows[1][0] == "B2B"
