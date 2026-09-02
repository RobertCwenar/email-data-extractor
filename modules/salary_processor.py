from typing import Literal

from offer import JobContract

ContractType = Literal[
    "UoP",
    "B2B",
    "UZ",
]

SalaryPeriod = Literal[
    "hourly",
    "monthly",
    "yearly",
]


class SalaryProcessor:
    monthly_working_hours = 168

    CONTRACT_PRIORITY: list[ContractType] = [
        "UoP",
        "B2B",
        "UZ",
    ]

    def select_contract(
        self,
        contracts: list[JobContract],
    ) -> JobContract | None:

        if not contracts:
            return None

        for contract_type in self.CONTRACT_PRIORITY:
            for contract in contracts:
                if contract.contract_type == contract_type:
                    return contract

        return None

    def normalize_salary(
        self,
        contract: JobContract,
    ) -> JobContract:

        if contract.contract_type == "Umowa zlecenie":
            contract.contract_type = "UZ"
        elif contract.contract_type == "Umowa o pracę":
            contract.contract_type = "UoP"

        if contract.contract_type is None:
            if contract.vat is True:
                contract.contract_type = "B2B"
            else:
                contract.contract_type = "UoP"

        if contract.vat is not True:
            contract.vat = None

        if contract.salary_min_offer is None:
            return contract

        if contract.salary_period == "hourly":
            contract.salary_min_monthly = contract.salary_min_offer * self.monthly_working_hours

            if contract.salary_max_offer is not None:
                contract.salary_max_monthly = contract.salary_max_offer * self.monthly_working_hours
        elif contract.salary_period == "daily":
            contract.salary_min_monthly = contract.salary_min_offer * (self.monthly_working_hours / 8)

            if contract.salary_max_offer is not None:
                contract.salary_max_monthly = contract.salary_max_offer * (self.monthly_working_hours / 8)

        elif contract.salary_period == "monthly":
            contract.salary_min_monthly = contract.salary_min_offer
            contract.salary_max_monthly = contract.salary_max_offer

        elif contract.salary_period == "yearly":
            contract.salary_min_monthly = contract.salary_min_offer / 12

            if contract.salary_max_offer is not None:
                contract.salary_max_monthly = contract.salary_max_offer / 12

        return contract

    def get_salary_status(self, contract: JobContract) -> str:

        if contract.salary_min_offer is None and contract.salary_max_offer is None:
            return "estimated"

        if contract.salary_period == "monthly":
            return "offer"

        return "offer_calculate"
