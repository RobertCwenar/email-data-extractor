from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from offer import JobOffer
from parsers.email_parser import EmailParser


@pytest.mark.asyncio
async def test_fetch_offers_returns_offer_text_and_cache_id():
    ai = MagicMock()
    db = MagicMock()
    filter_service = MagicMock()
    cache = MagicMock()
    email_config = {
        "host": "test",
        "port": 993,
        "user": "test",
        "password": "test",
    }

    salary_processor = MagicMock()

    parser = EmailParser(
        ai_service=ai,
        db_service=db,
        filter_service=filter_service,
        email_config=email_config,
        folder_name="TEST",
        source="Pracuj.pl",
        cache=cache,
        salary_parser=salary_processor,
    )

    # fake mail
    mail = MagicMock()

    parser._connect = MagicMock(return_value=mail)
    parser._get_mail_ids = MagicMock(return_value=[b"1"])

    msg = MagicMock()
    msg.__getitem__.side_effect = lambda key: "Sun, 30 Aug 2026 10:00:00 +0200" if key == "Date" else None

    parser._fetch_mail = MagicMock(return_value=msg)
    parser._get_html = MagicMock(return_value="<html>test</html>")

    offer = JobOffer(
        title="Analityk Danych",
        company="Datumo",
        location="Wrocław",
    )

    ai.parser_offers_api = AsyncMock(return_value=[offer])

    salary_processor.extract_offer_text.return_value = {id(offer): "salary offer text"}

    cache.contains.return_value = False

    with patch.object(
        parser,
        "_html_to_text",
        return_value="offer text",
    ):
        result = await parser.fetch_offers()

    assert len(result) == 1

    returned_offer, offer_text, cache_id = result[0]

    assert returned_offer.title == "Analityk Danych"
    assert offer_text == "salary offer text"
    assert cache_id == "1"
