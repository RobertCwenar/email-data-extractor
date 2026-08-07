from modules.job_classifier import JobClassifier


def test_classify_level():
    classifier = JobClassifier()

    print("LEVELS:", classifier.levels)
    print("CATEGORIES:", classifier.categories)

    result = classifier.classify_level("Senior Data Engineer")

    assert result == "senior"


def test_classify_category():
    classifier = JobClassifier()

    result = classifier.classify_category("Starszy specjalista ds. logistyki")

    assert result == "Logistyka"


def test_unknown_level():
    classifier = JobClassifier()

    result = classifier.classify_level("Something Random")

    assert result is None
