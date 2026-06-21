import pytest

from unittest.mock import MagicMock, patch

from main_parser.linkedin_parser import main

@pytest.mark.asyncio

async def test_main_loop_skips_processed_ids():
    mock_mail = MagicMock()
    test_main_loop_skips_processed_ids

    mail_ids = [b'26', b'27']
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value = ["26\n"]

        with patch('linkedin_parser.process_linkedin_block', new_callable=MagicMock) as mock_ai, \
            patch('linkedin_parser.save_offers', new_callable=MagicMock) as mock_save:
        
            clean_jobs =[]
            total = await main(mock_mail, mail_ids, clean_jobs)

            assert mock_ai.call_count == 1

            assert total >= 0

            print(f"Debug: Test is finished - find only new mails!")