from config import config
from offer import JobOffer
from services.filter_service import FilterService


def test_save_valid_offer():
    filter = FilterService(config)

    offer = JobOffer(title="Python Developer", company="Astom", date="2024-01-01", location="Remote")
    assert filter.should_save(offer) is True


def test_not_save_valid_offer():
    filter = FilterService(config)

    offer = JobOffer(title="Zobacz więcej ofert", company="ABC", date="2024-01-01", location="Remote")
    assert filter.should_save(offer) is False
