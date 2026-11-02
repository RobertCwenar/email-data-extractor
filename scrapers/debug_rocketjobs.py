from playwright.sync_api import sync_playwright

URL = "https://rocketjobs.pl/oferta-pracy/modivo-platform-kontroler-finansowy-k-m--wroclaw-bi-data"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    card = (
        page.locator("div.MuiBox-root.mui-dhmim1")
        .filter(has=page.locator('a[title="Zobacz ofertę Kontroler finansowy (k/m)"]'))
        .first
    )

    print("Liczba znalezionych kart:", card.count())

    if card.count() == 0:
        print("Nie znaleziono karty oferty.")
    else:
        print(
            "Ikona map-pin:",
            card.locator("svg.lucide-map-pin").count(),
        )

        location_selector = "div:has(> div > svg.lucide-map-pin) > p"
        locations = card.locator(location_selector)

        print("Liczba elementów lokalizacji:", locations.count())
        print("Lokalizacje:", locations.all_inner_texts())

        direct_selector = "div.mui-3h9qtu > p.mui-gtp4go"
        direct_locations = card.locator(direct_selector)

        print(
            "Liczba elementów w selektorze bezpośrednim:",
            direct_locations.count(),
        )
        print(
            "Lokalizacje bezpośrednie:",
            direct_locations.all_inner_texts(),
        )

        print("\nHTML karty:")
        print(card.evaluate("(element) => element.outerHTML"))

    input("\nNaciśnij Enter, aby zamknąć przeglądarkę...")
    browser.close()
