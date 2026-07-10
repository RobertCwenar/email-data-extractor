from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from main_parser.pracuj_pl_parser import main


@pytest.mark.asyncio
async def test_main_loop_flow():
    mock_mail = MagicMock()

    mail_ids = [b"220"]
    clean_jobs: list = []

    processed_ids: set[str] = set()

    # don't call main yet; set up mocks first so the loop can fetch and process

    # Mock the fetch method to return a sample email
    raw_email = b"Date: Sat, 20 Jun 2026 12:00:00 +0000\r\nContent-Type: text/html\r\n\r\n<html>Test</html>"
    mock_mail.fetch.return_value = ("OK", [(None, raw_email)])

    with patch("main_parser.pracuj_pl_parser.process_pracuj_block", new_callable=AsyncMock) as mock_ai:
        await main(mock_mail, mail_ids, clean_jobs, processed_ids)

        mock_ai.assert_called_once()
