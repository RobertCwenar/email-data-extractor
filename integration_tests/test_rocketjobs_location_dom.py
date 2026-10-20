from playwright.sync_api import sync_playwright

from scrapers.scraper_offer_adapter import rocketjobs_card_to_record


def test_rocketjobs_card_reads_location_from_current_dom_structure() -> None:
    html = """
    <div class="offer-card-container">
      <a class="offer-card" href="/oferta-pracy/data-analyst">Zobacz ofertę</a>
      <div>
        <a class="offer_list_offer_title_link">Data Analyst</a>
        <img alt="Acme">
        <div class="company-and-meta">
          <div class="company"><svg class="lucide-building"></svg><p>Acme</p></div>
          <button>
            <div class="location-content">
              <svg class="lucide-map-pin"></svg><div class="city">Wroc&#322;aw</div>, +4
              <div class="locations-label"> Lokalizacje</div>
            </div>
          </button>
          <div><svg class="lucide-building2"></svg><p>Zdalnie</p><p>Zdalnie</p></div>
        </div>
      </div>
    </div>
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        record = rocketjobs_card_to_record(page.locator("a.offer-card"), "https://rocketjobs.pl/oferty-pracy")
        browser.close()

    assert record is not None
    assert record["location"] == "Wroc\u0142aw"
    assert record["work_mode"] == "Zdalnie"
    assert record["url"] == "https://rocketjobs.pl/oferta-pracy/data-analyst"
