from typing import NamedTuple

from database.inserts import InsertDB
from modules.ai_service import AIService
from modules.filter_service import FilterService
from modules.processed_cache import FileCache
from parsers.email_parser import EmailParser
from parsers.salary_parsers import SalaryParser


class EmailSource(NamedTuple):
    folder: str
    source: str
    cache_file: str


EMAIL_SOURCES: tuple[EmailSource, ...] = (
    EmailSource("RocketJobs", "RocketJobs", "processed_rocketjobs_mails.txt"),
    EmailSource("PRACA", "Pracuj.pl", "processed_praca_mails.txt"),
    EmailSource("Link", "Linkedin", "processed_linkedin_mails.txt"),
    EmailSource("justjoinit", "justjoin.it", "processed_justjoinit_mails.txt"),
    EmailSource("theprotocol", "theprotocol.it", "processed_theprotocolit_mails.txt"),
    EmailSource("Jooble", "Jooble", "processed_jooble_mails.txt"),
)


def build_email_parsers(
    *,
    ai: AIService,
    db_insert: InsertDB,
    filter_service: FilterService,
    email_config: dict,
    salary_parser: SalaryParser,
) -> list[EmailParser]:
    return [
        EmailParser(
            ai,
            db_insert,
            filter_service,
            email_config,
            spec.folder,
            cache=FileCache(f"mail_records/{spec.cache_file}"),
            source=spec.source,
            salary_parser=salary_parser,
        )
        for spec in EMAIL_SOURCES
    ]
