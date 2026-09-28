from unittest.mock import Mock

from modules.salary_processor import SalaryProcessor


def test_backfill_salary_from_previous_offer():
    db = Mock()

    db.get_previous_offer.return_value = 10
    db.get_job_contracts.side_effect = [
        [],
        [
            (
                1,
                "UoP",
                "PLN",
                "monthly",
                8000,
                10000,
                8000,
                10000,
            )
        ],
    ]

    processor = SalaryProcessor(db)

    processor.backfill_salary_from_previous_offer(
        offer_id=20,
        title="Data Analyst",
        company="ABC",
    )

    db.save_job_contract.assert_called_once()

    contract = db.save_job_contract.call_args.args[0]

    assert contract.offer_id == 20
    assert contract.contract_type == "UoP"
    assert contract.salary_currency == "PLN"
    assert contract.salary_period == "monthly"
    assert contract.salary_min_offer == 8000
    assert contract.salary_max_offer == 10000
    assert contract.salary_min_monthly == 8000
    assert contract.salary_max_monthly == 10000

    db.update_offer_salary.assert_called_once_with(
        20,
        8000,
        10000,
        "offer",
    )


def test_backfill_does_nothing_when_previous_offer_has_no_contract():
    db = Mock()

    db.get_salary_status.return_value = None
    db.get_previous_offer.return_value = 10
    db.get_job_contracts.return_value = []

    processor = SalaryProcessor(db)

    processor.backfill_salary_from_previous_offer(
        offer_id=20,
        title="Data Analyst",
        company="ABC",
    )

    db.save_job_contract.assert_not_called()
    db.update_offer_salary.assert_not_called()


def test_backfill_does_nothing_when_previous_offer_does_not_exist():
    db = Mock()

    db.get_job_contracts.return_value = []
    db.get_previous_offer.return_value = None

    processor = SalaryProcessor(db)

    processor.backfill_salary_from_previous_offer(
        offer_id=20,
        title="Data Analyst",
        company="ABC",
    )

    db.get_job_contracts.assert_called_once_with(20)
    db.get_previous_offer.assert_called_once_with(
        20,
        "Data Analyst",
        "ABC",
    )
    db.save_job_contract.assert_not_called()
    db.update_offer_salary.assert_not_called()


def test_backfill_does_nothing_when_previous_contract_has_no_salary():
    db = Mock()

    db.get_job_contracts.side_effect = [
        [],  # current offer
        [
            (
                1,
                "UoP",
                "PLN",
                "monthly",
                None,
                None,
                None,
                None,
            )
        ],
    ]
    db.get_previous_offer.return_value = 10

    processor = SalaryProcessor(db)

    processor.backfill_salary_from_previous_offer(
        offer_id=20,
        title="Data Analyst",
        company="ABC",
    )

    db.save_job_contract.assert_not_called()
    db.update_offer_salary.assert_not_called()
