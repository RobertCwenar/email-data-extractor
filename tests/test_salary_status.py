from modules.salary_estimator import SalaryEstimator
from offer import JobOffer


def test_salary_status():
    estimator = SalaryEstimator(None)

    job = JobOffer(
        title="Python Developer",
        company="Test Company",
        location="Wroclaw",
        salary_min=5000.0,
        salary_max=7000.0,
    )

    assert estimator.salary_status(job) == "offer"


def test_estimated():
    estimator = SalaryEstimator(None)
    job = JobOffer(title="Python Developer", company="Test ABC", location="Wroclaw", salary_min=None, salary_max=None)

    assert estimator.salary_status(job) == "estimated"
