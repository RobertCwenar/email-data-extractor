from typing import Literal

from offer import JobContract

ContractType = Literal[
    "UoP",
    "B2B",
    "UZ",
]

SalaryPeriod = Literal[
    "hourly",
    "daily",
    "weekly",
    "monthly",
    "yearly",
]


class SalaryProcessor:
    monthly_working_hours = 168
    weeks_per_year = 52
    months_per_year = 12

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

        if contract.salary_min_offer is None and contract.salary_max_offer is None:
            return contract

        if contract.salary_min_offer is None:
            contract.salary_min_offer = contract.salary_max_offer

        if contract.salary_max_offer is None:
            contract.salary_max_offer = contract.salary_min_offer

        if contract.salary_period is None:
            contract.salary_period = "monthly"

        # Both values are guaranteed to be present after the fallback logic above.
        assert contract.salary_min_offer is not None
        assert contract.salary_max_offer is not None

        if contract.salary_period == "hourly":
            contract.salary_min_monthly = contract.salary_min_offer * self.monthly_working_hours

            contract.salary_max_monthly = contract.salary_max_offer * self.monthly_working_hours
        elif contract.salary_period == "daily":
            contract.salary_min_monthly = contract.salary_min_offer * (self.monthly_working_hours / 8)
            contract.salary_max_monthly = contract.salary_max_offer * (self.monthly_working_hours / 8)

        elif contract.salary_period == "weekly":
            contract.salary_min_monthly = contract.salary_min_offer * self.weeks_per_year / self.months_per_year
            contract.salary_max_monthly = contract.salary_max_offer * self.weeks_per_year / self.months_per_year

        elif contract.salary_period == "monthly":
            contract.salary_min_monthly = contract.salary_min_offer
            contract.salary_max_monthly = contract.salary_max_offer

        elif contract.salary_period == "yearly":
            contract.salary_min_monthly = contract.salary_min_offer / self.months_per_year
            contract.salary_max_monthly = contract.salary_max_offer / self.months_per_year

        return contract

    def get_salary_status(self, contract: JobContract) -> str:

        if contract.salary_min_offer is None and contract.salary_max_offer is None:
            return "estimated"

        if contract.salary_period == "monthly":
            return "offer"

        return "offer_calculate"
