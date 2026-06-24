import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from main_parser.pracuj_pl_parser import main
import os 
@pytest.mark.asyncio
async def test_main_loop_flow():
    mock_mail = MagicMock()
    
    raw_email = b"Date: Sat, 20 Jun 2026 12:00:00 +0000\r\nContent-Type: text/html\r\n\r\n<html>Test</html>"
    mock_mail.fetch = MagicMock(return_value=('OK', [(None, raw_email)]))
    
    mail_ids = [b'220']
    clean_jobs = []
   
    import main_parser.pracuj_pl_parser as pracuj_pl_parser
    pracuj_pl_parser.processed_ids.clear()
    if os.path.exists(pracuj_pl_parser.cache_file):
        os.remove(pracuj_pl_parser.cache_file)

    with patch('pracuj_pl_parser.process_pracuj_block', new_callable=AsyncMock) as mock_ai:
        await main(mock_mail, mail_ids, clean_jobs)
        
        # DEBUG: if is failed is True
        assert mock_ai.called is True