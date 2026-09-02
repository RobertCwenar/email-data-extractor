from modules.salary_processor import SalaryProcessor
from offer import JobContract


def test_select_contract_uop():
    processor = SalaryProcessor()

    contracts = [
        JobContract(
            offer_id=1,
            contract_type="UZ",
            salary_period="monthly",
            salary_min_offer=5000,
            salary_max_offer=6000,
        ),
        JobContract(
            offer_id=1,
            contract_type="B2B",
            salary_period="monthly",
            salary_min_offer=7000,
            salary_max_offer=8000,
        ),
        JobContract(
            offer_id=1,
            contract_type="UoP",
            salary_period="monthly",
            salary_min_offer=9000,
            salary_max_offer=10000,
        ),
    ]

    result = processor.select_contract(contracts)

    assert result is not None
    assert result.contract_type == "UoP"


def test_select_contract_uop_b2b():
    processor = SalaryProcessor()

    contracts = [
        JobContract(
            offer_id=1,
            contract_type="UZ",
            salary_period="monthly",
            salary_min_offer=5000,
            salary_max_offer=7000,
        ),
        JobContract(
            offer_id=1,
            contract_type="B2B",
            salary_period="monthly",
            salary_min_offer=7000,
            salary_max_offer=10000,
        ),
    ]

    result = processor.select_contract(contracts)

    assert result is not None
    assert result.contract_type == "B2B"


def test_select_contract_type_returns_none_for_empty_list():
    processor = SalaryProcessor()

    result = processor.select_contract([])

    assert result is None


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
