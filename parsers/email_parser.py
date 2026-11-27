import email
import imaplib
import logging
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Any, cast

from bs4 import BeautifulSoup

from core.base_parser import BaseParser
from database.inserts import InsertDB
from modules.ai_service import AIService
from modules.filter_service import FilterService
from modules.processed_cache import FileCache
from offer import JobOffer
from parsers.salary_parser import SalaryParser

logger = logging.getLogger(__name__)


class EmailParser(BaseParser):
    def __init__(
        self,
        ai_service: AIService,
        db_service: InsertDB,
        filter_service: FilterService,
        email_config: Any,
        folder_name: str,
        source: str,
        cache: FileCache,
        salary_parser: SalaryParser,
    ) -> None:
        super().__init__(ai_service, db_service, filter_service, cache)
        self.email_config = email_config
        self.folder_name = folder_name
        self.source = source
        self.cache = cache
        self.salary_parser = salary_parser
        self._pending_cache_ids: set[str] = set()

    def commit_processed_messages(self) -> None:
        for cache_id in self._pending_cache_ids:
            self.cache.add(cache_id)
        self._pending_cache_ids.clear()

    def _connect(self) -> imaplib.IMAP4_SSL:
        logger.debug("Connecting to mail server %s:%s", self.email_config["host"], self.email_config["port"])
        mail = imaplib.IMAP4_SSL(
            self.email_config["host"],
            self.email_config["port"],
        )
        mail.login(
            self.email_config["user"],
            self.email_config["password"],
        )
        logger.debug("Authenticated to mail server; folder=%s", self.folder_name)
        return mail

    def _get_mail_ids(self, mail: imaplib.IMAP4_SSL) -> list[bytes]:
        mail.select(self.folder_name)

        status, response = mail.search(None, "UNSEEN")

        if status != "OK":
            return []

        return response[0].split()

    def _fetch_mail(self, mail: imaplib.IMAP4_SSL, mail_id: bytes) -> Message | None:
        status, msg_data = mail.fetch(mail_id.decode(), "(RFC822)")
        if status != "OK":
            return None

        if not msg_data or not msg_data[0]:
            return None

        return email.message_from_bytes(cast(bytes, msg_data[0][1]))

    def _get_html(self, msg: Message) -> str | None:
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

        logger.debug("Connecting to fetch unseen email offers: source=%s", self.source)
        mail = self._connect()
        logger.debug("Selecting folder and searching unseen messages: source=%s", self.source)
        mail_ids = self._get_mail_ids(mail)
        logger.debug("Found %s unseen messages: source=%s", len(mail_ids), self.source)

        for index, mail_id in enumerate(mail_ids, start=1):
            logger.debug(
                "Fetching message %s/%s: source=%s id=%s",
                index,
                len(mail_ids),
                self.source,
                mail_id.decode(errors="replace"),
            )
            cache_id = mail_id.decode()

            if self.cache.contains(cache_id):
                continue

            msg = self._fetch_mail(mail, mail_id)
            html = self._get_html(msg) if msg else None

            if not html or msg is None:
                if msg is not None:
                    self._pending_cache_ids.add(cache_id)
                continue

            text = self._html_to_text(html)

            offers = await self.ai.parser_offers_api(text)
            logger.info("Extracted %s offers from message %s/%s", len(offers), index, len(mail_ids))

            mail_date = parsedate_to_datetime(msg["Date"]).date().isoformat()

            offer_texts = self.salary_parser.extract_offer_text(
                text,
                offers,
            )

            for offer in offers:
                offer.date = mail_date

                offer_text = offer_texts.get(id(offer), "")
                offers_result.append((offer, offer_text, cache_id))

            self._pending_cache_ids.add(cache_id)
        logger.debug("Logging out from mail server: source=%s", self.source)
        mail.logout()
        logger.info("Email fetch finished: source=%s offers=%s", self.source, len(offers_result))
        return offers_result
