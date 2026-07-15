# Library

import asyncio
import email
import email.utils
import logging
import os
import sqlite3
import sys
from datetime import date as Date
from datetime import datetime
from email.message import Message
from imaplib import IMAP4_SSL
from pathlib import Path
from typing import Any, List, Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

sys.path.append(str(Path(__file__).parent.parent))

from config import config
from offer import JobOffer, OffersResponse

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s -%(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class BaseParser:
    def __init__(self, source: str, cache_file: str):
        # Load API
        self.client = genai.Client(api_key=os.getenv("KEY_API", "").strip().replace(",", ""))
        self.source = source
        self.cache_file = Path(cache_file)

    # Function to extract HTML content from an email message
    def get_html(self, msg: Message) -> Optional[str]:
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

    def is_valid_offer(self, offer: JobOffer) -> bool:
        pos = offer.title.strip()
        comp = offer.company.strip()

        if len(pos) < 3 or len(comp) < 2 or pos.lower() == "null" or comp.lower() == "null":
            return False

        # Rubbish
        bad_markers = ["zobacz", "rekrutuje", "więcej", "wszystkie"]
        if any(marker in pos.lower() for marker in bad_markers):
            return False
        return True

    # Define functions to analyze job offers and companies
    def looks_like_job(self, title: Optional[str]) -> bool:
        if not title or not isinstance(title, str):
            return False

        clean_title = title.lower()

        junk_phrases = config.get_list(["looks_like_job", "junk_phrases"])
        words = config.get_list(["looks_like_job", "word_phrases"])
        exclude = config.get_list(["looks_like_job", "exclude"])

        for junk in junk_phrases:
            clean_title = clean_title.replace(junk.lower(), "")

        is_match = any(w in clean_title for w in words)
        is_excluded = any(e in clean_title for e in exclude)

        # Logic: must match words AND must not match exclusions
        if is_match and not is_excluded:
            return True
        print(f" [DEBUG] Rejected: '{title}' | Match: {is_match} | Excluded: {is_excluded}")
        return False

    def is_job_trigger(self, line: Optional[str]) -> bool:
        lowercased_line = (line or "").lower()

        word_phrases = config.get_list(["is_job_trigger", "keywords"])

        result = any(k.lower() in lowercased_line for k in word_phrases)

        return result

    # Function to parse job offers from text using the API
    async def parser_offers_API(self, text: str) -> List[JobOffer]:
        prompt = f'Extract all job offers from this text mail:\n"{text}"'

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="models/gemini-3.1-flash-lite",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": OffersResponse.model_json_schema(),
                    "temperature": 0.0,
                },
            )
            if not response.parsed:
                return []
            try:
                parsed_response = OffersResponse.model_validate(response.parsed)
                return parsed_response.offers
            except Exception as parse_error:
                logger.error("Failed to validate parsed API response: %s", parse_error, exc_info=True)
                return []
        except Exception as e:
            logger.error(f"Error occurred while parsing offers: {e}", exc_info=True)
            return []

    # Entry point: Initialize the asyncio event loop and execute the main processing function
    async def run_parser(self, mail: Any, mail_ids: list[str]) -> int:
        cache_file = Path("mail_records/processed_rocketjobs_mails.txt")
        if not mail_ids:
            print("None new offers found.")
        else:
            print(f"Found {len(mail_ids)} new emails.")

        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                processed_ids = {line.strip() for line in f}
        else:
            processed_ids = set()

        clean_jobs: List[JobOffer] = []
        result = await self.main(mail, mail_ids, clean_jobs, processed_ids)
        return result

    # Main Loop
    async def process_block(
        self,
        text: str,
        current_date: datetime,
        clean_jobs: List[JobOffer],
    ):
        raise NotImplementedError

    async def main(
        self,
        mail: IMAP4_SSL,
        mail_ids: List[Any],
        clean_jobs: List[JobOffer],
        processed_ids: set[str],
    ) -> int:

        total_added = 0

        if self.cache_file.exists():
            with open(self.cache_file, "r") as f:
                processed_ids.update(line.strip() for line in f)

        for i in mail_ids:
            mail_id_str = i.decode() if isinstance(i, bytes) else str(i)

            if mail_id_str in processed_ids:
                continue

            status, msg_data = mail.fetch(i, "(RFC822)")

            if status != "OK":
                continue

            if msg_data and isinstance(msg_data[0], tuple):
                raw_email = msg_data[0][1]

                if isinstance(raw_email, bytes):
                    msg = email.message_from_bytes(raw_email)
                else:
                    continue
            else:
                continue

            date_header = msg.get("Date")
            current_date = email.utils.parsedate_to_datetime(date_header) if date_header else datetime.now()

            html = self.get_html(msg)

            if not html:
                with open(self.cache_file, "a") as f:
                    f.write(mail_id_str + "\n")

                processed_ids.add(mail_id_str)
                continue

            text = BeautifulSoup(html, "html.parser").get_text("\n")

            await self.process_block(
                text,
                current_date,
                clean_jobs,
            )

            await asyncio.sleep(55)

            for job in clean_jobs:
                self.save_offers(
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    date=job.date,
                    source=self.source,
                )

                total_added += 1

            clean_jobs.clear()

            with open(self.cache_file, "a") as f:
                f.write(mail_id_str + "\n")

            processed_ids.add(mail_id_str)

            print(f"Processed mail: {mail_id_str}, wait 35 seconds...")

        return total_added

    # Add new jobs offers to database file
    def save_offers(
        self,
        title: str,
        company: str,
        location: str,
        date: Date,
        source: str,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        db_name: str = "new_offers.db",
    ):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(
            """
                INSERT INTO Offers (title, company, location, salary_min, salary_max, date, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, company, location, salary_min, salary_max, date, source),
        )

        conn.commit()
        conn.close()
