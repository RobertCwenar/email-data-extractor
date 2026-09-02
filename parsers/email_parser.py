import email
import imaplib
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Optional

from bs4 import BeautifulSoup

from core.base_parser import BaseParser
from modules.ai_service import AIService
from modules.db_save import Database
from modules.filter_service import FilterService
from modules.processed_cache import FileCache
from offer import JobOffer
from parsers.salary_parsers import SalaryParser


class EmailParser(BaseParser):
    def __init__(
        self,
        ai_service: AIService,
        db_service: Database,
        filter_service: FilterService,
        email_config,
        folder_name: str,
        source: str,
        cache: FileCache,
        salary_parser: SalaryParser,
    ):
        super().__init__(ai_service, db_service, filter_service, cache)
        self.email_config = email_config
        self.folder_name = folder_name
        self.source = source
        self.cache = cache
        self.salary_parser = salary_parser

    def _connect(self):
        mail = imaplib.IMAP4_SSL(
            self.email_config["host"],
            self.email_config["port"],
        )
        mail.login(
            self.email_config["user"],
            self.email_config["password"],
        )
        return mail

    def _get_mail_ids(self, mail):
        mail.select(self.folder_name)

        status, response = mail.search(None, "UNSEEN")

        if status != "OK":
            return []

        return response[0].split()

    def _fetch_mail(self, mail, mail_id):
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
        if status != "OK":
            return None

        return email.message_from_bytes(msg_data[0][1])

    def _get_html(self, msg: Message) -> Optional[str]:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        return payload.decode("utf-8", errors="ignore")
                    if isinstance(payload, str):
                        return payload
        else:
            if msg.get_content_type() == "text/html":
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode("utf-8", errors="ignore")
                if isinstance(payload, str):
                    return payload
        return None

    def _html_to_text(self, html: str) -> str:
        return BeautifulSoup(html, "html.parser").get_text("\n")

    # Function to extract HTML content from an email message
    async def fetch_offers(self) -> list[tuple[JobOffer, str, str]]:
        offers_result: list[tuple[JobOffer, str, str]] = []

        mail = self._connect()
        mail_ids = self._get_mail_ids(mail)

        for mail_id in mail_ids:
            cache_id = mail_id.decode()

            if self.cache.contains(cache_id):
                continue

            msg = self._fetch_mail(mail, mail_id)
            html = self._get_html(msg) if msg else None

            if not html or msg is None:
                continue

            text = self._html_to_text(html)

            offers = await self.ai.parser_offers_api(text)

            mail_date = parsedate_to_datetime(msg["Date"]).date().isoformat()

            offer_texts = self.salary_parser.extract_offer_text(
                text,
                offers,
            )

            for offer in offers:
                offer.date = mail_date

                offer_text = offer_texts.get(id(offer), "")
                offers_result.append((offer, offer_text, cache_id))

            self.cache.add(cache_id)
        mail.logout()
        return offers_result
