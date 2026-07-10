from datetime import datetime
from typing import Any, Dict, Optional, cast

import pytest
from pydantic import BaseModel


class JobOffer(BaseModel):
    date: datetime
    title: str
    company: str
    location: str
    salary: Optional[float] = None


# Fixture to provide a sample JobOffer instance for testing


@pytest.fixture
def sample_job_offer():
    return JobOffer(
        date=datetime(2023, 10, 1), title="Software Engineer", company="Tech Corp", location="Warsaw", salary=8000
    )


def test_job_offer_model(sample_job_offer):
    assert sample_job_offer.title == "Software Engineer"
    assert isinstance(sample_job_offer.date, datetime)
    assert sample_job_offer.company == "Tech Corp"
    assert sample_job_offer.location == "Warsaw"
    assert sample_job_offer.salary == 8000


def test_job_offer_serialization():
    data = [
        {
            "date": "2023-10-01T00:00:00",
            "title": "Software Engineer",
            "company": "Tech Corp",
            "location": "Warsaw",
            "salary": 8000,
        },
        {
            "date": "2023-11-15T00:00:00",
            "title": "Data Scientist",
            "company": "Data Inc",
            "location": "Krakow",
            "salary": 9000,
        },
        {
            "date": "2023-10-01T00:00:00",
            "title": "DevOps Engineer",
            "company": "Cloud Solutions",
            "location": "Gdansk",
            "salary": 8500,
        },
        {
            "date": "2023-12-01T00:00:00",
            "title": "Product Manager",
            "company": "Startup Ltd",
            "location": "Wroclaw",
            "salary": None,
        },
    ]

    offers = [JobOffer(**cast(Dict[str, Any], item)) for item in data]
    assert len(offers) == 4
    assert offers[0].title == "Software Engineer"
    assert offers[1].title == "Data Scientist"
    assert offers[2].title == "DevOps Engineer"
    assert offers[3].title == "Product Manager"
    print("All job offers serialized successfully.")


if __name__ == "__main__":
    import pytest

    pytest.main(["-v", "tests/test_pydantic.py"])
    print("Everything is working correctly.")
