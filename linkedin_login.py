from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir="linkedni_profile",
        headless=False,
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://www.linkedin.com/login")

    input("Log in to LinkedIn, then press Enter here...")

    context.close()
