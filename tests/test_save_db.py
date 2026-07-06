import os
import sqlite3

import pytest

from init_database import init_db
from main_parser.pracuj_pl_parser import save_offers


@pytest.fixture
def test_db():

    db_name = "test_offers.db"
    # Cleanup previous test database if it exists
    if os.path.exists(db_name):
        os.remove(db_name)

    init_db(db_name)
    yield db_name

    # Cleanup after test
    if os.path.exists(db_name):
        os.remove(db_name)


def test_saving_offers(test_db):
    # Example offer
    mock_job = {
        "title": "Python Developer",
        "company": "Software House",
        "location": "Wroclaw",
        "salary": "15000",
        "date": "20.06.2026",
        "source": "pracuj.pl",
    }

    save_offers(
        mock_job["title"],
        mock_job["company"],
        mock_job["location"],
        mock_job["salary"],
        mock_job["date"],
        mock_job["source"],
        db_name=test_db,
    )

    #
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM Offers")
    result = cursor.fetchone()
    conn.close()

    assert result[0] == "Python Developer"
    print("Test regarding: The offer has been saved in the test version!")
