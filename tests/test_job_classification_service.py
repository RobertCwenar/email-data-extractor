from unittest.mock import MagicMock

import pytest

from modules.job_classification_service import JobClassificationService
from offer import JobContract


def make_service():
    queries = MagicMock()
    queries.db._connect.return_value.__enter__.return_value = MagicMock()
    updates = MagicMock()
    inserts = MagicMock()
    classifier = MagicMock()
    estimator = MagicMock()
    processor = MagicMock()

    def normalize(contract):
        if contract.salary_period == "hourly" and contract.salary_min_offer is not None:
            contract.salary_min_monthly = contract.salary_min_offer * 168
            contract.salary_max_monthly = contract.salary_max_offer * 168
        return contract

    processor.normalize_salary.side_effect = normalize
    processor.select_contract.side_effect = lambda contracts: contracts[0] if contracts else None
    processor.get_salary_status.return_value = "offer"

    return (
        JobClassificationService(queries, updates, inserts, classifier, estimator, processor),
        queries,
        updates,
        processor,
    )


@pytest.mark.asyncio
async def test_salary_selection_normalizes_contracts_updates_changed_rows_and_offer():
    service, queries, updates, processor = make_service()
    queries.get_job_contracts.return_value = [
        (8, "B2B", "PLN", "hourly", 50, 60, None, None),
    ]

    await service.process_salary_selection({21})

    contract = processor.normalize_salary.call_args.args[0]
    conn = queries.db._connect.return_value.__enter__.return_value
    assert contract == JobContract(
        offer_id=21,
        contract_type="B2B",
        salary_currency="PLN",
        salary_period="hourly",
        salary_min_offer=50,
        salary_max_offer=60,
        salary_min_monthly=8400,
        salary_max_monthly=10080,
    )
    updates.update_job_contract_monthly.assert_called_once_with(8, 8400, 10080, conn)
    updates.update_offer_salary.assert_called_once_with(
        offer_id=21,
        salary_min=8400,
        salary_max=10080,
        salary_status="offer",
        conn=conn,
    )


@pytest.mark.asyncio
async def test_salary_selection_skips_offer_update_when_no_contract_is_selected():
    service, queries, updates, processor = make_service()
    queries.get_job_contracts.return_value = []
    processor.select_contract.return_value = None

    await service.process_salary_selection({21})

    processor.select_contract.assert_called_once_with([])
    updates.update_offer_salary.assert_not_called()
    updates.update_job_contract_monthly.assert_not_called()
