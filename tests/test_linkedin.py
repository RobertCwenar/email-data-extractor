from unittest.mock import MagicMock, mock_open, patch

import pytest

from main_parser.linkedin_parser import main


@pytest.mark.asyncio
async def test_main_loop_skips_processed_ids():
    mock_mail = MagicMock()

    mail_ids = [b"26", b"27"]
    mock_file_content = "26\n27\n"

    m = mock_open(read_data=mock_file_content)

    processed_ids: set[str] = set()

    with patch("builtins.open", m):
        with patch("main_parser.linkedin_parser.save_offers", new_callable=MagicMock) as mock_save:
            clean_jobs: list = []

            total = await main(mock_mail, mail_ids, clean_jobs, processed_ids)

            mock_save.assert_not_called()
            assert total >= 0
