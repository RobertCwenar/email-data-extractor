import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import scraper_config
from orchestrator import main
from scrapers.justjoin_scraper import JustJoinScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.pracuj_scraper import Scraper
from scrapers.rocketjobs_scraper import RocketJobsScraper
from scrapers.theprotocol_scraper import TheProtocolScraper


@pytest.mark.asyncio
async def test_main_runs_real_scraper_classes_with_mocked_page_fetches(tmp_path, monkeypatch):
    pracuj_url = "https://pracuj.example/jobs"
    linkedin_url = "https://linkedin.example/jobs"
    rocketjobs_url = "https://rocketjobs.example/jobs"
    justjoin_url = "https://justjoin.example/jobs"
    theprotocol_url = "https://theprotocol.example/jobs"

    def configured_urls(keys):
        if keys == ["scraper", "urls"]:
            return [pracuj_url]
        if keys == ["scraper_linkedin", "urls"]:
            return [linkedin_url]
        if keys == ["scraper_rocketjobs", "urls"]:
            return [rocketjobs_url]
        if keys == ["scraper_justjoinit", "urls"]:
            return [justjoin_url]
        if keys == ["scraper_theprotocolit", "urls"]:
            return [theprotocol_url]
        return []

    monkeypatch.setattr(scraper_config, "get_list", configured_urls)
    monkeypatch.setattr(Scraper, "output_file", str(tmp_path / "filter_pracuj_offers.json"))
    monkeypatch.setattr(
        LinkedInScraper,
        "output_file",
        str(tmp_path / "filter_linkedin_offers.json"),
    )
    monkeypatch.setattr(
        RocketJobsScraper,
        "output_file",
        str(tmp_path / "filter_rocketjobs_offers.json"),
    )
    monkeypatch.setattr(
        JustJoinScraper,
        "output_file",
        str(tmp_path / "filter_justjoin_offers.json"),
    )
    monkeypatch.setattr(
        TheProtocolScraper,
        "output_file",
        str(tmp_path / "filter_theprotocol_offers.json"),
    )

    pracuj_offers = [
        {
            "title": "Data Analyst",
            "company": "Example Pracuj",
            "location": "Warszawa",
            "level": "Junior",
            "contract": None,
            "work_mode": None,
            "salary": None,
            "url": "https://pracuj.example/praca/data-analyst,oferta,1001",
        }
    ]
    linkedin_offers = [
        {
            "title": "Data Engineer",
            "company": "Example LinkedIn",
            "location": "Warszawa",
            "level": None,
            "contract": None,
            "work_mode": "Praca hybrydowa",
            "salary": None,
            "url": "https://www.linkedin.com/jobs/view/2002",
            "offer_id": "2002",
        }
    ]
    rocketjobs_offers = [
        {
            "title": "BI Analyst",
            "company": "Example RocketJobs",
            "location": "Wrocław",
            "level": "Specjalista / Mid",
            "contract": "B2B",
            "work_mode": "Hybrydowo",
            "salary": "12 000 PLN/mies.",
            "url": "https://rocketjobs.example/oferta-pracy/bi-analyst",
        }
    ]
    justjoin_offers = [
        {
            "title": "Data Operations Analyst",
            "company": "Example JustJoin",
            "location": "Warszawa",
            "level": "Mid",
            "contract": "Permanent",
            "work_mode": "Hybrid",
            "salary": None,
            "url": "https://justjoin.it/job-offer/example-data-operations-analyst-warszawa-data",
            "offer_id": "example-data-operations-analyst-warszawa-data",
        }
    ]
    theprotocol_offers = [
        {
            "title": "SQL Data Analyst",
            "company": "Example Protocol",
            "location": "Krakow",
            "contract": "B2B",
            "work_mode": "Hybrid",
            "salary": None,
            "url": "https://theprotocol.it/praca/sql-data-analyst%2Coferta%2C12345",
            "offer_id": "12345",
        }
    ]

    mock_offer = MagicMock()
    mock_offer.title = "Python Developer"
    mock_offer.company = "Krzysiumo"
    mock_offer.date = "2026-09-28"

    mock_parser = MagicMock()
    mock_parser.source = "RocketJobs"
    mock_parser.fetch_offers = AsyncMock(return_value=[(mock_offer, "salary text", "cache-1")])

    mock_ai = MagicMock()
    mock_ai.validate_salary_api = AsyncMock(return_value=[])

    mock_db = MagicMock()
    mock_db_insert = MagicMock()
    mock_db_insert.save_offers.side_effect = [101, 102, 103, 104, 105, 106]
    mock_db_query = MagicMock()
    mock_db_update = MagicMock()
    mock_db_schema = MagicMock()

    mock_db_query.get_offer_history.return_value = []
    mock_db_query.get_offers_for_status.return_value = []
    mock_db_query.get_salary_history.return_value = []
    mock_db_query.get_job_contract_offer_ids.return_value = []
    mock_db_query.find_same_source_duplicate_id.return_value = None

    mock_filter = MagicMock()
    mock_filter.should_save.return_value = True

    with (
        patch("orchestrator.AIService", return_value=mock_ai),
        patch("orchestrator.Database", return_value=mock_db),
        patch("orchestrator.InsertDB", return_value=mock_db_insert),
        patch("orchestrator.QueryDB", return_value=mock_db_query),
        patch("orchestrator.UpdateDB", return_value=mock_db_update),
        patch("orchestrator.DBSchema", return_value=mock_db_schema),
        patch("orchestrator.FilterService", return_value=mock_filter),
        patch("orchestrator.build_email_parsers", return_value=[mock_parser]),
        patch("orchestrator.Deduplication", return_value=mock_db_query),
        patch.object(Scraper, "get_offers_from_page", return_value=pracuj_offers) as pracuj_fetch,
        patch.object(
            LinkedInScraper,
            "get_offers_from_page",
            return_value=linkedin_offers,
        ) as linkedin_fetch,
        patch.object(
            RocketJobsScraper,
            "get_offers_from_page",
            return_value=rocketjobs_offers,
        ) as rocketjobs_fetch,
        patch.object(
            JustJoinScraper,
            "get_offers_from_page",
            return_value=justjoin_offers,
        ) as justjoin_fetch,
        patch.object(
            TheProtocolScraper,
            "get_offers_from_page",
            return_value=theprotocol_offers,
        ) as theprotocol_fetch,
    ):
        await main()

    pracuj_fetch.assert_called_once_with(pracuj_url)
    linkedin_fetch.assert_called_once_with(linkedin_url)
    rocketjobs_fetch.assert_called_once_with(rocketjobs_url)
    justjoin_fetch.assert_called_once_with(justjoin_url)
    theprotocol_fetch.assert_called_once_with(theprotocol_url)
    assert mock_filter.should_save.call_count == 6
    assert mock_db_insert.save_offers.call_count == 6
    mock_db_update.normalize_offer_locations.assert_called_once_with()
    rocketjobs_call = next(
        call for call in mock_db_insert.save_offers.call_args_list if call.kwargs.get("source") == "scraper_rocketjobs"
    )
    (rocketjobs_saved_offer,) = rocketjobs_call.args
    assert rocketjobs_saved_offer.title == "BI Analyst"
    saved_sources = {call.kwargs["source"] for call in mock_db_insert.save_offers.call_args_list}
    assert "scraper_justjoinit" in saved_sources
    assert "scraper_theprotocol" in saved_sources

    pracuj_saved = json.loads((tmp_path / "filter_pracuj_offers.json").read_text(encoding="utf-8"))
    linkedin_saved = json.loads((tmp_path / "filter_linkedin_offers.json").read_text(encoding="utf-8"))
    rocketjobs_saved = json.loads((tmp_path / "filter_rocketjobs_offers.json").read_text(encoding="utf-8"))
    justjoin_saved = json.loads((tmp_path / "filter_justjoin_offers.json").read_text(encoding="utf-8"))
    theprotocol_saved = json.loads((tmp_path / "filter_theprotocol_offers.json").read_text(encoding="utf-8"))
    assert pracuj_saved[0]["offer_id"] == "1001"
    assert linkedin_saved[0]["offer_id"] == "2002"
    assert rocketjobs_saved[0]["title"] == "BI Analyst"
    assert justjoin_saved[0]["offer_id"] == "example-data-operations-analyst-warszawa-data"
    assert theprotocol_saved[0]["offer_id"] == "12345"


@pytest.mark.asyncio
async def test_main_retries_once_with_saved_scraper_data_after_failure():
    run_pipeline = AsyncMock(side_effect=[RuntimeError("temporary AI failure"), None])
    wait = AsyncMock()

    with (
        patch("orchestrator._run_pipeline", run_pipeline),
        patch("orchestrator.asyncio.sleep", wait),
    ):
        await main()

    assert run_pipeline.await_count == 2
    assert run_pipeline.await_args_list[0].kwargs == {"skip_scrapers": False}
    assert run_pipeline.await_args_list[1].kwargs == {"skip_scrapers": True}
    wait.assert_awaited_once_with(60)
