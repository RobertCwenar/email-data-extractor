import json
import logging
from datetime import datetime

from playwright.sync_api import Locator, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

JOB_CARD_SELECTOR = '[componentkey^="job-card-component-ref-"]'


class LinkedInScraper:
    def __init__(self) -> None:
        self.source = "scraper_linkedin"
        self.url = "https://www.linkedin.com/jobs/search-results/?keywords=Analityk%20danych&geoId=105072130"

    def get_text(self, card: Locator, selector: str) -> str | None:
        element = card.locator(selector).first
        if element.count() == 0:
            return None
        return element.inner_text(timeout=3000).strip()

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
                JOB_CARD_SELECTOR,
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

        logger.info(
            "LinkedIn scrolling: rounds=%s, reached bottom=%s",
            scroll_rounds,
            reached_bottom,
        )
        return reached_bottom

    def read_page_offers(self, cards: Locator) -> list[dict]:
        offers: list[dict] = []
        for card in cards.all():
            component_key = card.get_attribute("componentkey")
            offer_id = component_key.removeprefix("job-card-component-ref-") if component_key else None

            title = self.get_text(card, "p span[aria-hidden='true']")
            paragraphs = card.locator("p")
            company = paragraphs.nth(1).inner_text().strip() if paragraphs.count() > 1 else None
            location_text = paragraphs.nth(2).inner_text().strip() if paragraphs.count() > 2 else None

            work_mode = None
            location = location_text
            if location_text:
                for mode in ("Praca stacjonarna", "Praca hybrydowa", "Praca zdalna"):
                    if mode in location_text:
                        work_mode = mode
                        location = location_text.replace(f" ({mode})", "").strip()
                        break

            offers.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "level": None,
                    "contract": None,
                    "work_mode": work_mode,
                    "salary": None,
                    "url": f"https://www.linkedin.com/jobs/view/{offer_id}" if offer_id else None,
                    "offer_id": offer_id,
                }
            )
        return offers

    def get_offers_from_page(self) -> list[dict]:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir="linkedni_profile",
                headless=False,
            )
            page = context.pages[0] if context.pages else context.new_page()

            page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            offers: list[dict] = []
            seen_keys: set[str] = set()
            max_pages = 40

            for page_number in range(1, max_pages + 1):
                cards = page.locator(JOB_CARD_SELECTOR)
                self.scroll_results_to_bottom(page, cards)
                page_offers = self.read_page_offers(cards)
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
                        arg={"selector": JOB_CARD_SELECTOR, "previous": current_keys},
                        timeout=20000,
                    )
                except PlaywrightTimeoutError:
                    logger.warning("LinkedIn: failed to load page %s", page_number + 1)
                    break
            else:
                logger.warning("LinkedIn reached the page limit: %s", max_pages)

            return offers

    def run_scraper(self) -> list[dict]:
        offers = self.get_offers_from_page()
        timestamp = datetime.now().strftime("%Y-%m-%d")

        for offer in offers:
            offer["scraped_at"] = timestamp

        output_file = "filter_linkedin_offers.json"

        try:
            with open(output_file, "r", encoding="utf-8") as file:
                existing_offers = json.load(file)
                if not isinstance(existing_offers, list):
                    existing_offers = []
        except FileNotFoundError, json.JSONDecodeError:
            existing_offers = []
        existing_keys = {(offer.get("offer_id"), offer.get("scraped_at")) for offer in existing_offers}

        new_offers = []
        for offer in offers:
            offer_key = offer.get("offer_id") or offer.get("url")
            key = (offer_key, offer["scraped_at"])
            if offer_key is None or key not in existing_keys:
                new_offers.append(offer)
                if offer_key is not None:
                    existing_keys.add(key)

        existing_offers.extend(new_offers)

        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(existing_offers, file, ensure_ascii=False, indent=2)

        logger.info("New LinkedIn offers: %s", len(new_offers))
        return new_offers
