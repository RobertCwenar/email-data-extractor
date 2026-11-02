import re

import pytest


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("Wrocław", "Wrocław"),
        ("Wrocław\n, +4\nLokalizacje", "Wrocław"),
        ("Warszawa, +2 Lokalizacje", "Warszawa"),
        ("Kraków", "Kraków"),
    ],
)
def test_location_normalization(raw_text, expected):
    text = re.sub(r"\s+", " ", raw_text).strip()

    match = re.match(
        r"^(.+?)(?:\s*,\s*\+\d+)?(?:\s+lokalizacje)?$",
        text,
        re.IGNORECASE,
    )

    location = match.group(1).strip() if match else text

    assert location == expected
