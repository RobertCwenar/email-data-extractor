from unittest.mock import MagicMock

from modules.salary_history import SalaryHistory


def test_real_salary_lookup_uses_only_matching_company_and_title_history():
    queries = MagicMock()
    queries.get_salary_history.return_value = [
        (1, "Data Analyst", "Acme", 7000, 9000, "2026-11-10", "data_analytics", "junior"),
        (2, "Data Analyst", "Acme", 6000, 8000, "2026-10-01", "data_analytics", "junior"),
        (3, "Data Analyst", "Other Co", 5000, 7000, "2026-11-11", "data_analytics", "junior"),
        (4, "Data Analyst", "Acme", None, None, "2026-11-12", "data_analytics", "junior"),
    ]
    history = SalaryHistory(queries)
    history.process_history()

    assert history.find_real_salary("Acme", "Data Analyst", "2026-11-25") == (7000.0, 9000.0)
