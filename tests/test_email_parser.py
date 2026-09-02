from modules.salary_processor import SalaryProcessor
from offer import JobContract


def test_select_uop_over_b2b():
    processor = SalaryProcessor()

    contracts = [
        JobContract(
            offer_id=1,
            contract_type="B2B",
            salary_currency="PLN",
            salary_period="hourly",
            salary_min_offer=35,
            salary_max_offer=45,
        ),
        JobContract(
            offer_id=1,
            contract_type="UoP",
            salary_currency="PLN",
            salary_period="monthly",
            salary_min_offer=7000,
            salary_max_offer=9000,
        ),
    ]

    for contract in contracts:
        processor.normalize_salary(contract)

    selected_contract = processor.select_contract(contracts)

    assert selected_contract is not None
    assert selected_contract.contract_type == "UoP"
    assert selected_contract.salary_min_monthly == 7000
    assert selected_contract.salary_max_monthly == 9000
    assert processor.get_salary_status(selected_contract) == "offer"
