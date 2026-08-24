import statistics


class SalaryStatistics:
    def median_salary(self, salaries: list[float]) -> float | None:
        if not salaries:
            return None

        return statistics.median(salaries)

    def average_salary(self, salaries: list[float]) -> float | None:
        if not salaries:
            return None

        return statistics.mean(salaries)

    def minimum_salary(self, salaries: list[float]) -> float | None:
        if not salaries:
            return None

        return min(salaries)

    def maximum_salary(self, salaries: list[float]) -> float | None:
        if not salaries:
            return None

        return max(salaries)

    def standard_deviation(self, salaries: list[float]) -> float | None:
        if len(salaries) < 2:
            return None

        return statistics.stdev(salaries)
