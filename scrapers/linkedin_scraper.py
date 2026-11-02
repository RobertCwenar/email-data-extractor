import logging
from typing import Any

from playwright.sync_api import Locator, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import scraper_config
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_offer_adapter import LINKEDIN_CARD_SELECTOR, linkedin_card_to_record

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    output_file = "filter_linkedin_offers.json"
    source = "scraper_linkedin"

    def __init__(self) -> None:
        self.urls = scraper_config.get_list(["scraper_linkedin", "urls"])

    def scroll_results_to_bottom(self, page, cards: Locator) -> bool:
        previous_keys = set(
            cards.evaluate_all(
                "elements => elements.map(element => element.getAttribute('componentkey')).filter(Boolean)"
            )
        )
        stable_rounds = 0
        max_scroll_rounds = 40
        reached_bottom = False
        scroll_rounds = 0

        for _ in range(max_scroll_rounds):
            scroll_rounds += 1
            if not previous_keys:
                break

            scroll_position = page.evaluate(
                """selector => {
                    const card = document.querySelector(selector);
                    const isScrollable = element => {
                        const style = window.getComputedStyle(element);
                        return /(auto|scroll)/.test(style.overflowY)
                            && element.scrollHeight > element.clientHeight + 20;
                    };

                    const namedLeftPane = document.querySelector(
                        '.scaffold-layout__list, .jobs-search-results-list, [class*="jobs-search-results-list"]'
                    );
                    let target = namedLeftPane && isScrollable(namedLeftPane)
                        ? namedLeftPane
                        : null;

                    if (!target) {
                        let parent = card && card.parentElement;
                        while (parent && parent !== document.body) {
                            const rect = parent.getBoundingClientRect();
                            const isLeftPane = rect.left < window.innerWidth * 0.55;
                            if (isLeftPane && isScrollable(parent)) {
                                target = parent;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                    }

                    if (target) {
                        const step = Math.max(target.clientHeight * 0.8, 400);
                        target.scrollTop = Math.min(
                            target.scrollTop + step,
                            target.scrollHeight
                        );
                        target.dispatchEvent(new Event('scroll', { bubbles: true }));
                        return {
                            pane: 'left-results',
                            top: target.scrollTop,
                            height: target.scrollHeight,
                            at_bottom: target.scrollTop + target.clientHeight
                                >= target.scrollHeight - 10
                        };
                    }

                    window.scrollBy(0, Math.max(window.innerHeight * 0.8, 600));
                    const pageHeight = document.documentElement.scrollHeight;
                    return {
                        pane: 'page-fallback',
                        top: window.scrollY,
                        at_bottom: window.scrollY + window.innerHeight >= pageHeight - 10
                    };
                }""",
                LINKEDIN_CARD_SELECTOR,
            )
            page.wait_for_timeout(2000)

            current_keys = set(
                cards.evaluate_all(
                    "elements => elements.map(element => element.getAttribute('componentkey')).filter(Boolean)"
                )
            )
            if current_keys - previous_keys:
                stable_rounds = 0
                logger.info("Loaded additional LinkedIn offers: %s", len(current_keys))
            else:
                stable_rounds += 1

            previous_keys = current_keys
            at_bottom = bool(isinstance(scroll_position, dict) and scroll_position.get("at_bottom"))
            if stable_rounds >= 3 and at_bottom:
                reached_bottom = True
                break

        logger.debug(
            "LinkedIn scrolling: rounds=%s, reached bottom=%s",
            scroll_rounds,
            reached_bottom,
        )
        return reached_bottom

    def get_offers_from_page(self, url: str) -> list[dict[str, Any]]:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir="linkedni_profile",
                headless=False,
            )
            page = context.pages[0] if context.pages else context.new_page()

            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            offers: list[dict[str, Any]] = []
            seen_keys: set[str] = set()
            max_pages = 40

            for page_number in range(1, max_pages + 1):
                cards = page.locator(LINKEDIN_CARD_SELECTOR)
                self.scroll_results_to_bottom(page, cards)
                page_offers = [linkedin_card_to_record(card) for card in cards.all()]
                for offer in page_offers:
                    key = offer.get("offer_id") or offer.get("url")
                    if key is None or key not in seen_keys:
                        offers.append(offer)
                        if key is not None:
                            seen_keys.add(key)

                logger.info(
                    "LinkedIn page %s: cards=%s, unique offers collected=%s",
                    page_number,
                    len(page_offers),
                    len(offers),
                )

                current_keys = cards.evaluate_all(
                    "elements => elements.map(element => element.getAttribute('componentkey')).filter(Boolean)"
                )
                next_page = page.get_by_role("button", name=f"Strona {page_number + 1}", exact=True).first
                if next_page.count() == 0:
                    next_page = page.get_by_role("button", name="Dalej", exact=True).first
                if next_page.count() == 0 or not next_page.is_enabled():
                    break

                next_page.click()
                try:
                    page.wait_for_function(
                        """args => {
                            const keys = Array.from(document.querySelectorAll(args.selector))
                                .map(element => element.getAttribute('componentkey'));
                            return keys.some(key => key && !args.previous.includes(key));
                        }""",
                        arg={"selector": LINKEDIN_CARD_SELECTOR, "previous": current_keys},
                        timeout=20000,
                    )
                except PlaywrightTimeoutError:
                    logger.warning("LinkedIn: failed to load page %s", page_number + 1)
                    break
            else:
                logger.warning("LinkedIn reached the page limit: %s", max_pages)

            return offers
