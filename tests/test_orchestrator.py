from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator import main


@pytest.mark.asyncio
async def test_main():

    # Mock offers
    mock_offer = MagicMock()
    mock_offer.title = "Python Developer"
    mock_offer.company = "Krzysiumo"
    mock_offer.date = "2026-09-28"

    # Mock parser
    mock_parser_instance = MagicMock()
    mock_parser_instance.source = "RocketJobs"
    mock_parser_instance.fetch_offers = AsyncMock(return_value=[(mock_offer, "salary text", "cache-1")])

    # Mock AI
    mock_ai_instance = MagicMock()
    mock_ai_instance.validate_salary_api = AsyncMock(return_value=[])

    # Mock DB
    mock_db = MagicMock()
    mock_db_insert = MagicMock()
    mock_db_queries = MagicMock()
    mock_db_update = MagicMock()
    mock_db_schema = MagicMock()

    mock_db_queries.get_offer_history.return_value = []
    mock_db_queries.get_offers_for_status.return_value = []
    mock_db_queries.get_salary_history.return_value = []
    mock_db_queries.get_job_contract_offer_ids.return_value = []

    # Mock filter
    mock_filter_instance = MagicMock()
    mock_filter_instance.should_save.return_value = True

    with (
        patch("orchestrator.AIService", return_value=mock_ai_instance),
        patch("orchestrator.Database", return_value=mock_db),
        patch("orchestrator.InsertDB", return_value=mock_db_insert),
        patch("orchestrator.QueryDB", return_value=mock_db_queries),
        patch("orchestrator.UpdateDB", return_value=mock_db_update),
        patch("orchestrator.DBSchema", return_value=mock_db_schema),
        patch("orchestrator.FilterService", return_value=mock_filter_instance),
        patch(
            "orchestrator.build_email_parsers",
            return_value=[mock_parser_instance],
        ),
    ):
        await main()

    assert mock_parser_instance.fetch_offers.call_count == 1
    assert mock_filter_instance.should_save.call_count == 1
    assert mock_db_insert.save_offers.call_count == 1
