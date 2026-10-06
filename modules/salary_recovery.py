import email
import imaplib
from datetime import date
from email.message import Message

from bs4 import BeautifulSoup

from offer import JobContract

SOURCE_FOLDERS = {
    "RocketJobs": "RocketJobs",
    "Pracuj.pl": "PRACA",
    "Linkedin": "Link",
    "justjoin.it": "justjoinit",
    "theprotocol.it": "theprotocol",
    "Jooble": "Jooble",
}


class SalaryRecovery:
    def __init__(
        self,
        db_query,
        db_insert,
        db_update,
        ai,
        email_config,
        salary_processor,
    ):
        self.db_query = db_query
        self.db_insert = db_insert
        self.db_update = db_update
        self.ai = ai
        self.email_config = email_config
        self.salary_processor = salary_processor

    async def recover(self, offer_id: int) -> bool:
        with self.db_query.db._connect() as conn:
            if self.db_query.get_job_contracts(offer_id, conn):
                print("Recovery stopped: contracts already exist")
                return False

        offer = self.db_query.get_offer(offer_id)

        if offer is None:
            print("Recovery stopped: offer does not exist")
            return False

        title = offer[1]
        company = offer[2]
        mail_date = offer[6]
        source = offer[7]
        folder_name = SOURCE_FOLDERS[source]

        print(f"Recovery: {title} | {company}")
        print(f"Date: {mail_date}")
        print(f"Source: {source}")
        print(f"Folder: {folder_name}")

        contracts = await self._recover_from_mail(
            title=title,
            company=company,
            mail_date=mail_date,
            folder_name=folder_name,
        )

        if not contracts:
            previous = self.db_query.get_previous_offer_with_salary(
                offer_id,
                title,
                company,
            )

            if previous:
                (
                    _,
                    salary_min,
                    salary_max,
                    salary_status,
                    contract_type,
                    salary_currency,
                    salary_period,
                    salary_min_offer,
                    salary_max_offer,
                    salary_min_monthly,
                    salary_max_monthly,
                ) = previous

                self.db_update.update_offer_salary(
                    offer_id,
                    salary_min,
                    salary_max,
                    salary_status,
                )

                contract = JobContract(
                    offer_id=offer_id,
                    contract_type=contract_type,
                    salary_currency=salary_currency,
                    salary_period=salary_period,
                    salary_min_offer=salary_min_offer,
                    salary_max_offer=salary_max_offer,
                    salary_min_monthly=salary_min_monthly,
                    salary_max_monthly=salary_max_monthly,
                )

                self.db_insert.save_job_contract(contract)

                return True

            contract = JobContract(
                offer_id=offer_id,
            )

            self.db_insert.save_job_contract(contract)

            return True

        for contract in contracts:
            contract.offer_id = offer_id

            self.db_insert.save_job_contract(contract)

            self.db_update.update_offer_salary(
                offer_id,
                contract.salary_min_monthly,
                contract.salary_max_monthly,
                self.salary_processor.get_salary_status(contract),
            )

        return True

    def _connect(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL(
            self.email_config["host"],
            self.email_config["port"],
        )

        mail.login(
            self.email_config["user"],
            self.email_config["password"],
        )

        return mail

    async def _recover_from_mail(
        self,
        title: str,
        company: str,
        mail_date: str,
        folder_name: str,
    ):
        mail = self._connect()

        try:
            parsed_date = date.fromisoformat(mail_date)

            mail_ids = self._get_mail_ids_by_date(
                mail,
                parsed_date,
                folder_name,
            )

            normalized_title = self._normalize(title)
            normalized_company = self._normalize(company)

            for mail_id in mail_ids:
                msg = self._fetch_mail(
                    mail,
                    mail_id,
                )

                if msg is None:
                    continue

                text = self._get_text(msg)

                if not text:
                    continue

                normalized_text = self._normalize(text)

                if normalized_title not in normalized_text or normalized_company not in normalized_text:
                    continue

                offer_text = self._extract_offer_text(
                    text,
                    title,
                )

                if not offer_text:
                    continue

                contracts = await self._validate_salary(
                    offer_text,
                )

                if contracts:
                    return contracts

            return []

        finally:
            mail.logout()

    def _get_mail_ids_by_date(
        self,
        mail: imaplib.IMAP4_SSL,
        mail_date: date,
        folder_name: str,
    ) -> list[bytes]:
        mail.select(folder_name)

        imap_date = mail_date.strftime("%d-%b-%Y")

        status, response = mail.search(
            None,
            "ON",
            imap_date,
        )

        if status != "OK":
            return []

        return response[0].split()

    def _fetch_mail(
        self,
        mail: imaplib.IMAP4_SSL,
        mail_id: bytes,
    ) -> Message | None:
        status, msg_data = mail.fetch(
            mail_id.decode(),
            "(RFC822)",
        )

        if status != "OK":
            return None

        if not msg_data or not msg_data[0]:
            return None

        payload = msg_data[0]

        if not isinstance(payload, tuple) or len(payload) < 2:
            return None

        message_bytes = payload[1]

        if not isinstance(message_bytes, bytes):
            return None

        return email.message_from_bytes(
            message_bytes,
        )

    def _get_text(self, msg: Message) -> str | None:
        html = self._get_html(msg)

        if html:
            return BeautifulSoup(
                html,
                "html.parser",
            ).get_text("\n")

        if msg.get_content_type() == "text/plain":
            payload = msg.get_payload(decode=True)

            if isinstance(payload, bytes):
                return payload.decode(
                    "utf-8",
                    errors="ignore",
                )

            if isinstance(payload, str):
                return payload

        return None

    def _get_html(self, msg: Message) -> str | None:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() != "text/html":
                    continue

                payload = part.get_payload(decode=True)

                if isinstance(payload, bytes):
                    return payload.decode(
                        "utf-8",
                        errors="ignore",
                    )

                if isinstance(payload, str):
                    return payload

        elif msg.get_content_type() == "text/html":
            payload = msg.get_payload(decode=True)

            if isinstance(payload, bytes):
                return payload.decode(
                    "utf-8",
                    errors="ignore",
                )

            if isinstance(payload, str):
                return payload

        return None

    def _extract_offer_text(
        self,
        text: str,
        title: str,
    ) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        normalized_title = self._normalize(title)

        for index, line in enumerate(lines):
            if normalized_title in self._normalize(line):
                return "\n".join(lines[index:])

        return None

    async def _validate_salary(
        self,
        offer_text: str,
    ):
        return await self.ai.validate_salary_api(
            offer_text,
        )

    def _normalize(self, text: str) -> str:
        return " ".join(text.casefold().split())
