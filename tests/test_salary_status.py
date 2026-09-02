from modules.salary_processor import SalaryProcessor
from offer import JobContract


def test_salary_status():
    processor = SalaryProcessor()

    job = JobContract(
        offer_id=1,
        contract_type="UoP",
        salary_currency="PLN",
        salary_period="monthly",
        salary_min_offer=7000,
        salary_max_offer=9000,
        salary_min_monthly=7000,
        salary_max_monthly=9000,
    )

    assert processor.get_salary_status(job) == "offer"


def test_estimated():
    processor = SalaryProcessor()

    job = JobContract(
        offer_id=1,
        contract_type="UoP",
        salary_currency="PLN",
        salary_period="hourly",
        salary_min_offer=None,
        salary_max_offer=None,
        salary_min_monthly=7200,
        salary_max_monthly=9600,
    )

    assert processor.get_salary_status(job) == "estimated"


def test_offer_calculated():
    processor = SalaryProcessor()

    job = JobContract(
        offer_id=1,
        contract_type="UoP",
        salary_currency="PLN",
        salary_period="yearly",
        salary_min_offer=200000,
        salary_max_offer=300000,
        salary_min_monthly=16666.67,
        salary_max_monthly=25000.00,
    )

    assert processor.get_salary_status(job) == "offer_calculate"
