import statistics


class MedianSalary:
    def median_salary(self, salaries):

        if not salaries:
            return None

        return statistics.median(salaries)
