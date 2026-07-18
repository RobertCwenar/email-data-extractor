from offer import JobOffer
from services.filter_service import FilterService


class FakeConfig:
    def get_list(self, keys):
        if keys == ["is_valid_offer", "bad_markers"]:
            return ["Zobacz więcej ofert", "Logo firmy"]
        if keys == ["looks_like_job", "word_phrases"]:
            return ["developer", "engineer", "programmer"]

        if keys == ["looks_like_job", "junk_phrases"]:
            return []

        if keys == ["looks_like_job", "exclude"]:
            return []

        return []


def test_save_valid_offer():
    filter_service = FilterService(FakeConfig())

    offer = JobOffer(title="Python Developer", company="Astom", date="2024-01-01", location="Remote")
    assert filter_service.should_save(offer) is True


def test_not_save_valid_offer():
    filter_service = FilterService(FakeConfig())

    offer = JobOffer(title="Zobacz więcej ofert", company="ABC", date="2024-01-01", location="Remote")

    assert filter_service.should_save(offer) is False
