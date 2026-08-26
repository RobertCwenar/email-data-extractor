from typing import Literal

from offer import JobContract

ContractType = Literal[
    "UoP",
    "B2B",
    "UZ",
]

SalaryPeriod = Literal[
    "hour",
    "month",
    "year",
]


class SalaryProcessor:
    MONTHLY_WORKING_HOURS = 168

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

        if contract.salary_min_offer is None:
            return contract

        if contract.salary_period == "hour":
            contract.salary_min_monthly = contract.salary_min_offer * self.MONTHLY_WORKING_HOURS

            if contract.salary_max_offer is not None:
                contract.salary_max_monthly = contract.salary_max_offer * self.MONTHLY_WORKING_HOURS

        elif contract.salary_period == "month":
            contract.salary_min_monthly = contract.salary_min_offer
            contract.salary_max_monthly = contract.salary_max_offer

        elif contract.salary_period == "year":
            contract.salary_min_monthly = contract.salary_min_offer / 12

            if contract.salary_max_offer is not None:
                contract.salary_max_monthly = contract.salary_max_offer / 12

        return contract
