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
    ):
        super().__init__(ai_service, db_service, filter_service, cache)
        self.email_config = email_config
        self.folder_name = folder_name
        self.source = source
        self.cache = cache

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

    # Function to extract HTML content from an email message
    def _get_html(self, msg: Message) -> Optional[str]:
        if msg is None:
            return None

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        return payload.decode("utf-8", errors="ignore")
        elif msg.get_content_type() == "text/html":
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                return payload.decode("utf-8", errors="ignore")
        return None

    def _html_to_text(self, html: str) -> str:
        return BeautifulSoup(html, "html.parser").get_text("\n")

    async def fetch_offers(self) -> list[JobOffer]:
        offers_result = []

        mail = self._connect()
        mail_ids = self._get_mail_ids(mail)

        for mail_id in mail_ids:
            cache_id = mail_id.decode()

            if self.cache.contains(cache_id):
                continue

            msg = self._fetch_mail(mail, mail_id)

            if not msg:
                continue

            html = self._get_html(msg)
            if not html:
                continue

            text = self._html_to_text(html)

            offers = await self.ai.parser_offers_api(text)

            mail_date = parsedate_to_datetime(msg["Date"]).date().isoformat()

            for offer in offers:
                offer.date = mail_date
                offers_result.append(offer)

            self.cache.add(cache_id)

        mail.logout()

        return offers_result
