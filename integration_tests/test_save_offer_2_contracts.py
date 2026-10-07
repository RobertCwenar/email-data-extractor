from unittest.mock import MagicMock

from database.database import Database
from database.inserts import InsertDB
from offer import JobContract, JobOffer


def test_save_offer_with_uop_and_b2b():
    db_connection = MagicMock()
    db_connection.__enter__.return_value = db_connection
    db_cursor = db_connection.cursor.return_value

    db_cursor.fetchone.side_effect = [
        (1,),  # save_company
        (1,),  # save_offers
    ]

    db = Database()
    setattr(db, "_connect", MagicMock(return_value=db_connection))

    insert_db = InsertDB(db)

    offer = JobOffer(
        title="Analityk Danych",
        company="Datumo",
        location="Wrocław",
        salary_min=7000,
        salary_max=9000,
        date="2026-08-30",
        salary_status="offer",
    )

    offer_id = insert_db.save_offers(
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
        insert_db.save_job_contract(contract)

    assert db_cursor.execute.call_count == 5
