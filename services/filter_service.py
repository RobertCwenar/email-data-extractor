import logging
from typing import Optional

from offer import JobOffer


class FilterService:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def is_valid_offer(self, offer: JobOffer) -> bool:
        pos = offer.title.strip()
        comp = offer.company.strip()

        if len(pos) < 3 or len(comp) < 2 or pos.lower() == "null" or comp.lower() == "null":
            return False

        bad_markers = self.config.get_list(["is_valid_offer", "bad_markers"])
        if any(marker in pos.lower() for marker in bad_markers):
            return False
        return True

    def looks_like_job(self, title: Optional[str]) -> bool:
        if not title or not isinstance(title, str):
            return False

        clean_title = title.lower()

        junk_phrases = self.config.get_list(["looks_like_job", "junk_phrases"])
        words = self.config.get_list(["looks_like_job", "word_phrases"])
        exclude = self.config.get_list(["looks_like_job", "exclude"])

        for junk in junk_phrases:
            clean_title = clean_title.replace(junk.lower(), "")

        is_match = any(w in clean_title for w in words)
        is_excluded = any(e in clean_title for e in exclude)

        # Logic: must match words AND must not match exclusions
        if is_match and not is_excluded:
            return True
        self.logger.debug(f" [DEBUG] Rejected: '{title}' | Match: {is_match} | Excluded: {is_excluded}")
        return False

    def should_save(self, offer: JobOffer) -> bool:
        return self.is_valid_offer(offer) and self.looks_like_job(offer.title)
