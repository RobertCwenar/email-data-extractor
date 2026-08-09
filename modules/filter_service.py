import logging
import re
from typing import Optional

from offer import JobOffer

logger = logging.getLogger(__name__)


class FilterService:
    def __init__(self, config):
        self.config = config

    def is_valid_offer(self, offer: JobOffer) -> bool:
        pos = offer.title.strip()
        comp = offer.company.strip()

        if len(pos) < 3 or len(comp) < 2 or pos.lower() == "null" or comp.lower() == "null":
            return False

        bad_markers = self.config.get_list(["is_valid_offer", "bad_markers"])
        if any(marker.lower() in pos.lower() for marker in bad_markers):
            return False
        return True

    def looks_like_job(self, title: Optional[str]) -> bool:
        if not title or not isinstance(title, str):
            return False

        clean_title = title.lower()

        junk_phrases = self.config.get_list(["looks_like_job", "junk_phrases"])
        words = self.config.get_list(["looks_like_job", "word_phrases"])
        exclude = self.config.get_list(["looks_like_job", "excluded_phrases"])

        for junk in junk_phrases:
            clean_title = clean_title.replace(junk.lower(), "")

        is_match = any(w in clean_title for w in words)
        is_excluded = any(e in clean_title for e in exclude)

        # Logic: must match words AND must not match exclusions
        if is_match and not is_excluded:
            return True
        logger.debug(f" [DEBUG] Rejected: '{title}' | Match: {is_match} | Excluded: {is_excluded}")
        return False

    def normalize_company(self, company: str) -> str:
        result = company.strip()

        suffixes = self.config.get_list(["company_normalization", "remove_legal_forms"])

        for suffix in sorted(suffixes, key=len, reverse=True):
            pattern = rf"\s*{re.escape(suffix)}\s*$"

            result = re.sub(
                pattern,
                "",
                result,
                flags=re.IGNORECASE,
            ).strip()

        return result

    def should_save(self, offer: JobOffer) -> bool:
        offer.company = self.normalize_company(offer.company)

        valid = self.is_valid_offer(offer)
        job_like = self.looks_like_job(offer.title)

        logger.debug(f"{offer.title} | company: {offer.company} | valid: {valid} | looks_like_job: {job_like}")

        return valid and job_like
