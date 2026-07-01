import pytest
from main_parser.pracuj_pl_parser import run_parser, login

#Login to wp.pl
@pytest.mark.asyncio
async def test_login_email(mocker):
    mock_imap = mocker.patch("main_parser.pracuj_pl_parser.imaplib.IMAP4_SSL")
    mock_instance = mock_imap.return_value
    mock_instance.login.return_value = ("OK", [b'123 220'])
    
    # Mock the functions select and search to return expected values
    mail, mail_ids = await login()

    total_found = len(mail_ids)
    
    # Check that choose the correct mailbox
    mock_instance.select.assert_called_once_with("PRACA")
    
    # Check that thesearch UNSEEN mail
    mock_instance.search.assert_called_once_with(None, 'UNSEEN')
    
    # Check that the returned mail_ids and mail instance are as expected
    assert mail_ids == [b'123', b'220', b'230']
    assert mail == mock_instance
    assert total_found == 3

    print("Total Jobs found:", total_found)







