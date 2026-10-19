import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import scraper_config
from orchestrator import main
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.pracuj_scraper import Scraper


@pytest.mark.asyncio
async def test_main_runs_real_scraper_classes_with_mocked_page_fetches(tmp_path, monkeypatch):
    pracuj_url = "https://pracuj.example/jobs"
    linkedin_url = "https://linkedin.example/jobs"

    def configured_urls(keys):
        if keys == ["scraper", "urls"]:
            return [pracuj_url]
        if keys == ["scraper_linkedin", "urls"]:
            return [linkedin_url]
        return []

    monkeypatch.setattr(scraper_config, "get_list", configured_urls)
    monkeypatch.setattr(Scraper, "output_file", str(tmp_path / "filter_pracuj_offers.json"))
    monkeypatch.setattr(
        LinkedInScraper,
        "output_file",
        str(tmp_path / "filter_linkedin_offers.json"),
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
    mock_db_insert.save_offers.side_effect = [101, 102, 103]
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
    ):
        await main()

    pracuj_fetch.assert_called_once_with(pracuj_url)
    linkedin_fetch.assert_called_once_with(linkedin_url)
    assert mock_filter.should_save.call_count == 3
    assert mock_db_insert.save_offers.call_count == 3

    pracuj_saved = json.loads((tmp_path / "filter_pracuj_offers.json").read_text(encoding="utf-8"))
    linkedin_saved = json.loads((tmp_path / "filter_linkedin_offers.json").read_text(encoding="utf-8"))
    assert pracuj_saved[0]["offer_id"] == "1001"
    assert linkedin_saved[0]["offer_id"] == "2002"


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
