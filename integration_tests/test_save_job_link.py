import gc
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


def test_save_job_link(test_db):
    db = Database(test_db)

    job = JobOffer(
        title="Data Scientist",
        company="Technical company",
        location="Wroclaw",
        salary_min=12000.0,
        salary_max=16000.0,
        date="03.08.2026",
    )
    offer_id = db.save_offers(job, source="Pracuj.pl")

    db.save_job_link(offer_id, url="https://www.pracuj.pl/oferta/data-scientist", source="Pracuj.pl")

    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT offer_id, url, source
            FROM JobLinks
            """
        )

        result = cursor.fetchone()

    assert result is not None
    assert result[0] == offer_id
    assert result[1] == "https://www.pracuj.pl/oferta/data-scientist"
    assert result[2] == "Pracuj.pl"
