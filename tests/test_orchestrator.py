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
    mock_db_save = MagicMock()
    mock_db_read = MagicMock()
    mock_db_update = MagicMock()
    mock_db_tables = MagicMock()

    mock_db_read.get_offer_history.return_value = []
    mock_db_read.get_offers_for_status.return_value = []
    mock_db_read.get_salary_history.return_value = []
    mock_db_read.get_job_contract_offer_ids.return_value = []

    # Mock filter
    mock_filter_instance = MagicMock()
    mock_filter_instance.should_save.return_value = True

    with (
        patch("orchestrator.AIService", return_value=mock_ai_instance),
        patch("orchestrator.Database", return_value=mock_db),
        patch("orchestrator.DatabaseSave", return_value=mock_db_save),
        patch("orchestrator.DatabaseRead", return_value=mock_db_read),
        patch("orchestrator.DatabaseUpdate", return_value=mock_db_update),
        patch("orchestrator.DatabaseTables", return_value=mock_db_tables),
        patch("orchestrator.FilterService", return_value=mock_filter_instance),
        patch("orchestrator.EmailParser", return_value=mock_parser_instance),
        patch("orchestrator.FileCache"),
    ):
        await main()

    # Verify that offers were fetched from the parser
    assert mock_parser_instance.fetch_offers.call_count == 6

    # Verify that the offer passed the filtering rules
    assert mock_filter_instance.should_save.call_count == 6

    # Verify that the accepted offer was saved to the database
    assert mock_db_save.save_offers.call_count == 6
