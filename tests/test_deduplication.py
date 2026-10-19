from unittest.mock import MagicMock

from database.deduplication import Deduplication
from offer import JobOffer


def test_duplicate_lookup_is_limited_to_date_and_source():
    db = MagicMock()
    cursor = db._connect.return_value.__enter__.return_value.cursor.return_value
    cursor.fetchone.return_value = (27,)
    deduplication = Deduplication(db)
    offer = JobOffer(
        title="Data Analyst",
        company="Acme",
        location="Warsaw",
        date="2026-10-19",
    )

    duplicate_id = deduplication.find_same_source_duplicate_id(offer, "scraper_linkedin")

    assert duplicate_id == 27
    query, parameters = cursor.execute.call_args.args
    assert "date = %s" in query
    assert "title = %s" in query
    assert "company = %s" in query
    assert "source = %s" in query
    assert parameters == ("2026-10-19", "Data Analyst", "Acme", "scraper_linkedin")
