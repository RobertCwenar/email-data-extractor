from offer import JobOffer
from parsers.salary_parsers import SalaryParser


def test_extract_offer_text():
    text = """
    Specjalistka / Specjalista ds. Zakupów i Logistyki
    A-BIOTECH SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ
    Wrocław

    Data Analyst (Process Mining, BI)
    Capgemini Polska
    Wrocław (Fabryczna)

    QA Tester (m/f/d)
    60-90 zł netto (+ VAT) / godz.
    Next Technology Professionals Sp. z o.o.
    Warszawa

    Pracownik ds. Kalkulacji (k/m)
    Nagel Polska Sp. z o.o.
    Zabrze
    """

    offers = [
        JobOffer(
            title="Specjalistka / Specjalista ds. Zakupów i Logistyki",
            company="A-BIOTECH SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ",
            location="Wrocław",
        ),
        JobOffer(
            title="Data Analyst (Process Mining, BI)",
            company="Capgemini Polska",
            location="Wrocław (Fabryczna)",
        ),
        JobOffer(
            title="QA Tester (m/f/d)",
            company="Next Technology Professionals Sp. z o.o.",
            location="Warszawa",
        ),
        JobOffer(
            title="Pracownik ds. Kalkulacji (k/m)",
            company="Nagel Polska Sp. z o.o.",
            location="Zabrze",
        ),
    ]

    parser = SalaryParser()

    result = parser.extract_offer_text(text, offers)

    qa_text = result[id(offers[2])]

    assert "QA Tester (m/f/d)" in qa_text
    assert "60-90 zł netto (+ VAT) / godz." in qa_text
    assert "Next Technology Professionals Sp. z o.o." in qa_text
    assert "Warszawa" in qa_text

    assert "Data Analyst" not in qa_text
    assert "Pracownik ds. Kalkulacji" not in qa_text
