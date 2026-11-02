import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from scrapers.base_scraper import BaseScraper


class StubScraper(BaseScraper):
    def __init__(self, output_file: str, offers_by_url: dict[str, list[dict]]) -> None:
        self.urls = list(offers_by_url)
        self.output_file = output_file
        self.offers_by_url = offers_by_url
        self.visited_urls: list[str] = []

    def get_offers_from_page(self, url: str) -> list[dict]:
        self.visited_urls.append(url)
        return self.offers_by_url[url]


def test_run_scraper_validates_records_and_saves_to_its_output_file(tmp_path) -> None:
    output_file = tmp_path / "offers.json"
    url = "https://example.com/jobs"
    scraper = StubScraper(
        str(output_file),
        {
            url: [
                {
                    "title": "BI Engineer",
                    "company": "Jacumo",
                    "location": "Warszawa",
                    "work_mode": "Hybrid",
                    "url": "https://example.com/jobs/123",
                    "offer_id": "123",
                }
            ]
        },
    )

    new_offers = scraper.run_scraper()
    saved_offers = json.loads(output_file.read_text(encoding="utf-8"))

    assert scraper.visited_urls == [url]
    assert len(new_offers) == 1
    assert saved_offers == new_offers
    assert saved_offers[0]["title"] == "BI Engineer"
    assert saved_offers[0]["offer_id"] == "123"
    assert saved_offers[0]["level"] is None
    assert saved_offers[0]["contract"] is None
    assert saved_offers[0]["salary"] is None
    assert saved_offers[0]["scraped_at"] == datetime.now(ZoneInfo("Europe/Warsaw")).strftime("%Y-%m-%d")


def test_run_scraper_deduplicates_same_offer_on_same_day(tmp_path) -> None:
    output_file = tmp_path / "offers.json"
    url = "https://example.com/jobs"
    offer = {
        "title": "Data Engineer",
        "company": "Krzysiumo",
        "location": "Remote",
        "url": "https://example.com/jobs/456",
        "offer_id": "456",
    }
    scraper = StubScraper(str(output_file), {url: [offer]})

    first_run = scraper.run_scraper()
    second_run = scraper.run_scraper()
    saved_offers = json.loads(output_file.read_text(encoding="utf-8"))

    assert len(first_run) == 1
    assert second_run == []
    assert len(saved_offers) == 1


def test_run_scraper_dates_each_url_when_its_scrape_finishes(tmp_path, monkeypatch) -> None:
    class FakeDate:
        def __init__(self, value: str) -> None:
            self.value = value

        def strftime(self, _format: str) -> str:
            return self.value

    dates = iter(("2026-10-19", "2026-10-20"))

    class FakeDateTime:
        @staticmethod
        def now(_timezone: ZoneInfo | None = None) -> FakeDate:
            return FakeDate(next(dates))

    monkeypatch.setattr("scrapers.base_scraper.datetime", FakeDateTime)
    scraper = StubScraper(
        str(tmp_path / "offers.json"),
        {
            "https://example.com/first": [{"title": "Data Analyst", "company": "Jacumo", "location": "Warsaw"}],
            "https://example.com/second": [{"title": "Data Engineer", "company": "Jacumo", "location": "Warsaw"}],
        },
    )

    offers = scraper.run_scraper()

    assert [offer["scraped_at"] for offer in offers] == ["2026-10-19", "2026-10-20"]


def test_load_saved_offers_reads_only_today_without_visiting_urls(tmp_path) -> None:
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    output_file = tmp_path / "offers.json"
    output_file.write_text(
        json.dumps(
            [
                {
                    "title": "Current Offer",
                    "company": "Acme",
                    "location": "Warsaw",
                    "offer_id": "today-1",
                    "scraped_at": today,
                },
                {
                    "title": "Old Offer",
                    "company": "Acme",
                    "location": "Warsaw",
                    "offer_id": "yesterday-1",
                    "scraped_at": yesterday,
                },
            ]
        ),
        encoding="utf-8",
    )
    scraper = StubScraper(str(output_file), {"https://example.com/jobs": []})

    offers = scraper.load_saved_offers()

    assert len(offers) == 1
    assert offers[0]["offer_id"] == "today-1"
    assert scraper.visited_urls == []
