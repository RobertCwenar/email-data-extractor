from modules.salary_processor import SalaryProcessor
from offer import JobContract


def test_normalize_monthly_salary():
    processor = SalaryProcessor()

    contract = JobContract(
        offer_id=1,
        contract_type="UoP",
        salary_period="monthly",
        salary_min_offer=7000,
        salary_max_offer=9000,
    )

    result = processor.normalize_salary(contract)

    assert result.salary_min_monthly == 7000
    assert result.salary_max_monthly == 9000


def test_normalize_yearly_salary():
    processor = SalaryProcessor()

    contract = JobContract(
        offer_id=1,
        contract_type="UoP",
        salary_period="yearly",
        salary_min_offer=120000,
        salary_max_offer=180000,
    )

    result = processor.normalize_salary(contract)

    assert result.salary_min_monthly == 10000
    assert result.salary_max_monthly == 15000


def test_get_salary_status_for_missing_salary():
    processor = SalaryProcessor()

    contract = JobContract(
        offer_id=1,
        contract_type="UoP",
        salary_period="monthly",
    )

    assert processor.get_salary_status(contract) == "estimated"


def test_get_salary_status_for_monthly_salary():
    processor = SalaryProcessor()

    contract = JobContract(
        offer_id=1,
        contract_type="UoP",
        salary_period="monthly",
        salary_min_offer=7000,
        salary_max_offer=9000,
    )

    assert processor.get_salary_status(contract) == "offer"


def test_get_salary_status_for_hourly_salary():
    processor = SalaryProcessor()

    contract = JobContract(
        offer_id=1,
        contract_type="B2B",
        salary_period="hourly",
        salary_min_offer=34,
        salary_max_offer=45,
    )

    assert processor.get_salary_status(contract) == "offer_calculate"
