from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator import main


@pytest.mark.asyncio
async def test_main():

    # Mock offers
    mock_offer = MagicMock()
    mock_offer.title = "Python Developer"

    # Mock parser
    mock_parser_instance = MagicMock()
    mock_parser_instance.source = "RocketJobs"
    mock_parser_instance.fetch_offers = AsyncMock(return_value=[mock_offer])

    # Mock AI
    mock_ai_instance = MagicMock()

    # Mock DB
    mock_db_instance = MagicMock()

    # Mock filter
    mock_filter_instance = MagicMock()
    mock_filter_instance.should_save.return_value = True

    with (
        patch("orchestrator.AIService", return_value=mock_ai_instance),
        patch("orchestrator.Database", return_value=mock_db_instance),
        patch("orchestrator.FilterService", return_value=mock_filter_instance),
        patch("orchestrator.EmailParser", return_value=mock_parser_instance),
    ):
        await main()

    # Verify that offers were fetched from the parser
    assert mock_parser_instance.fetch_offers.call_count == 3

    # Verify that the offer passed the filtering rules
    assert mock_filter_instance.should_save.call_count == 3

    # Verify that the accepted offer was saved to the database
    assert mock_db_instance.save_offers.call_count == 3
