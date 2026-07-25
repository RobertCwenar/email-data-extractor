import gc
import logging
import os
import sqlite3
import time

import pytest

from database.init_database import init_db
from modules.db_save import Database
from offer import JobOffer


@pytest.fixture
def test_db(tmp_path):
    db_name = tmp_path / "test_offers.db"

    init_db(db_name)

    yield db_name

    gc.collect()

    time.sleep(0.5)

    if os.path.exists(db_name):
        os.remove(db_name)


def test_saving(test_db):
    job = JobOffer(
        title="Python Developer",
        company="Software House",
        location="Warsaw",
        salary_min=10000.0,
        salary_max=24000.0,
        date="20.07.2026",
    )

    db = Database(test_db)

    db.save_offers(job, source="Pracuj.pl")

    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, company, source FROM Offers")
        result = cursor.fetchone()

    assert result is not None
    assert result[0] == "Python Developer"
    assert result[1] == "Software House"
    assert result[2] == "Pracuj.pl"

    logging.info("Test regarding: The offer has been saved in the test version!")
