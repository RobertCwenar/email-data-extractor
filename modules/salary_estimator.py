import logging
from config import config 
from offer import JobOffer, JobClassification

class SalaryEstimator:
    def __init__(self):
        self.salary_rules = config.get_dict(["salary_rules"])

    def salary_status(self, job: JobOffer):

        if job.salary_min is not None or job.salary_max is not None:
            return "Values"

        elif job.salary_min is None and job.salary_max is None:
            return "estimated"

    def salary_logic(self, job: JobClassification):

        for category, level in self.salary_rules.items():

            if job.category == category:

                for level, salary in level.items():
                    if job.level == level:
        
                        base_salary = salary["base"]
                        salary_range = salary["range"]

                        salary_min = base_salary

                        salary_max = base_salary + salary_range

                        return salary_min, salary_max

   