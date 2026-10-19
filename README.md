# EMAIL DATA EXTRACTION

## Introduction

Job Data Extractor automates the monitoring of job offers and reduces the manual work of searching for opportunities and recording relevant information. It organizes offer data so it can be compared by role, company, location, experience level, and compensation.

Source code: [GitHub repository](https://github.com/RobertCwenar/email-data-extractor).

## About

The pipeline collects offers from configured email sources and the Pracuj.pl and LinkedIn job board scrapers. It validates and classifies offer data, normalizes salary and contract details, and stores the results in PostgreSQL. Salary history and configured rules can be used to estimate missing salary ranges.

## Technologies

### Language and Runtime

- Python 3.14+

### Database

- PostgreSQL
- SQL

### AI and Validation

- Google Gemini API
- Pydantic

### Web Scraping

- Playwright

### Testing and CI/CD

- pytest
- Ruff
- GitHub Actions

### Business Intelligence

- Power BI (planned)

## Features

- Extracts job offers from six configured email sources (RocketJobs, Pracuj.pl, LinkedIn, justjoin.it, theprotocol.it, and Jooble) and from the Pracuj.pl and LinkedIn web scrapers
- Parses, filters, deduplicates, and normalizes offer data
- Uses Pydantic models to validate data
- Stores offers and contract data in PostgreSQL
- Tracks salary history and estimates missing salary data
- Includes automated tests

## Project Results

- Automates the collection and processing of job offers from email and job board sources
- Centralizes offer, contract, and classification data in PostgreSQL
- Supports salary comparisons and estimates using collected salary history and configured rules

## Architecture

```text
Email sources (IMAP)                 Job board URLs
          |                      (Pracuj.pl, LinkedIn)
          v                             |
     Email parsers                      v
          |                    Scrapers and adapters
          +-------------+---------------+
                        v
           Filtering and cross-source deduplication
                        |
                        v
              Save offers and contracts
                        |
                        v
       Classification, estimation, and selection
                        |
                        v
             Update the same PostgreSQL database
```

The pipeline inserts offers and contracts before classification; the final step updates those records in the same PostgreSQL database. Power BI integration is planned and is not part of the current data flow.

## Usage and Installation

### 1. Clone the repository

```bash
git clone https://github.com/RobertCwenar/email-data-extractor.git
cd email-data-extractor
```

### 2. Install dependencies

The project requires Python 3.14 or newer. Install the project dependencies with `uv`:

```bash
uv sync
uv run playwright install chromium
```

### 3. Configure environment variables

Copy `.env_template` to `.env` and set the required mailbox, Gemini API, and PostgreSQL values. The variable names are `EMAIL`, `PASSWORD`, `EMAIL_HOST`, `EMAIL_PORT`, `KEY_API`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`. If `EMAIL_PORT` is omitted, the application uses `993`.

The active `filter_keywords.json` and `scraper_urls.json` files are local configuration. Create them from `filter_keywords_example.json` and `scraper_urls_example.json` before running the pipeline. The scraper example contains Pracuj.pl URLs; to enable LinkedIn scraping, add a `scraper_linkedin.urls` list to `scraper_urls.json`.

PostgreSQL must be running and reachable with the configured connection values. The application creates its tables when it starts.

### 4. Run the application

```bash
uv run python orchestrator.py
```

The application runs the configured email and scraper sources, processes the collected offers, and updates PostgreSQL. Scraped records are also written to `filter_pracuj_offers.json` and `filter_linkedin_offers.json`. Processed email IDs are tracked under `mail_records/` to avoid processing the same messages again.

## Additional Utilities

To recover salary data for one saved offer, run:

```bash
uv run python backfill_offer_status.py <offer_id>
```

The utility applies to offers from configured email sources. It searches the email folder and date associated with the offer. If it cannot validate salary from a matching message, it checks a previous matching offer with salary data.

To initialize the persistent LinkedIn browser profile, run `uv run python linkedin_login.py` and sign in when the browser opens.

The root SQL files provide queries, views, and triggers for manual analysis and database operations. See the [Technical Documentation](docs/technical.md) for details.

## Quality Checks and CI

Run the unit test suite with:

```bash
uv run pytest
```

Run Ruff checks and formatting with:

```bash
uv run ruff check .
uv run ruff format .
```

The GitHub Actions workflow runs on pull requests. It installs dependencies, prepares the active JSON configuration files from their examples, runs Ruff linting, and runs pytest. Tests use mocks for external services and database connections; CI does not connect to a live mailbox or PostgreSQL database.

## Project Structure

```text
/email-data-extractor
├── .devcontainer/
│   └── devcontainer.json
├── .github/
│   └── workflows/
│       └── ci.yml
├── core/
│   ├── __init__.py
│   └── base_parser.py
├── database/
│   ├── __init__.py
│   ├── connection.py
│   ├── deduplication.py
│   ├── inserts.py
│   ├── queries.py
│   ├── schema.py
│   ├── updates.py
│   └── db_operations/
│       ├── __init__.py
│       ├── migrate_status.py
│       ├── migration_db.py
│       └── migration_salary.py
├── docs/
│   ├── business.md
│   └── technical.md
│
│
│
├── integration_tests/
│   ├── __init__.py
│   ├── test_offers_db.py
│   └── test_save_offer_2_contracts.py
│
├── modules/
│   ├── __init__.py
│   ├── ai_service.py
│   ├── email_sources.py
│   ├── filter_service.py
│   ├── job_classification_service.py
│   ├── job_classifier.py
│   ├── offer_source_workflow.py
│   ├── offer_status.py
│   ├── processed_cache.py
│   ├── salary_estimator.py
│   ├── salary_history.py
│   ├── salary_processor.py
│   ├── salary_recovery.py
│   └── statistics_salary.py
│
├── parsers/
│   ├── __init__.py
│   ├── email_parser.py
│   └── salary_parser.py
│
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py
│   ├── linkedin_scraper.py
│   ├── pracuj_scraper.py
│   └── scraper_offer_adapter.py
│
├── tests/
│   ├── test_ai.py
│   ├── test_base_scraper.py
│   ├── test_classification.py
│   ├── test_email_parser.py
│   ├── test_filter_json.py
│   ├── test_filter_service.py
│   ├── test_job_classification_service.py
│   ├── test_json.py
│   ├── test_linkedin_scraper.py
│   ├── test_offer_source_workflow.py
│   ├── test_orchestrator.py
│   ├── test_pydantic.py
│   ├── test_salary_parser.py
│   ├── test_salary_processor_salary.py
│   ├── test_salary_processor_selection.py
│   ├── test_salary_status.py
│   ├── test_scraper.py
│   ├── test_scraper_record_to_contract.py
│   ├── test_update_status.py
│   └── test_validate_ai.py
│
├── .env_template
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── backfill_offer_status.py
├── config.py
├── filter_keywords_example.json
├── linkedin_login.py
├── offer.py
├── orchestrator.py
├── pyproject.toml
├── README.md
├── scraper_urls.json
├── scraper_urls_example.json

```

## Roadmap

### Completed

- Email-based job offer extraction
- Data validation with Pydantic
- Job level and category classification
- PostgreSQL database integration
- Salary estimation
- Salary history analysis
- Technical and business documentation

### In Progress

- Further improvements to employment contract handling and salary normalization
- Extended integration tests

### Planned

- Dedicated storage and tracking of job offer URLs in the database
- SQL-based analytical queries and reporting
- Power BI integration
