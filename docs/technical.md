# Technical Documentation

## 1. System Overview

The pipeline collects job offers from configured email sources and job-board scrapers. Email messages are read from their configured IMAP folders, while scraper URLs are configured separately.

After processing, the system saves the IDs of all processed emails in `mail_records`. This prevents the same email from being processed a second time. If an email is untracked but its ID is already saved in `mail_records`, it can be safely skipped. The individual ID stored in the file improves the email processing flow and enables individual monitoring of processed emails in the project.

The extracted email content is then processed and transformed into structured job offer data. Pydantic is used to validate the structure of the data, while AI-based classification is used to determine additional information about the job offer.

The application uses the `filter_keywords.json` configuration file to define filtering and classification rules. Based on these rules, irrelevant offers can be filtered out and relevant data can be assigned to the appropriate fields. When a category cannot be determined using the keywords defined in `filter_keywords.json`, the system uses AI classification to determine the appropriate category.

The processed data is stored in PostgreSQL, with `Offers` serving as the main table. Related data is stored in `JobContracts`, `JobDetails`, and `Companies`.

```text
Email / Scrapers
  ↓
Parsing
  ↓
JobOffer
  ↓
Filtering
  ↓
Classification
  ↓
Salary Estimation
  ↓
PostgreSQL
```

## 2. System Architecture

The system is designed as a modular ETL pipeline for processing job offers from multiple sources.

### 2.1 Data Flow

```text
Email and Scrapers
  ↓
EmailParser / Scraper Adapter
  ↓
JobOffer
  ↓
Filtering
  ↓
Offers
  ↓
Salary / Contracts
  ↓
JobClassification
  ↓
Salary Estimation
  ↓
Final Salary Selection
  ↓
Offers
  ↓
PostgreSQL
```

### 2.2 Main Components

- **EmailParser** – extracts job offer data from emails.
- **FilterService** – filters unwanted offers using configured rules.
- **AIService** – uses AI for structured data extraction and job offer analysis.
- **Pydantic Models** – validate and normalize application data.
- **Database Layer** – manages PostgreSQL schema creation, migrations, persistence, and data access.
- **JobClassifier** – determines job category and seniority based on configured classification rules.
- **JobClassificationService** – coordinates job classification and stores classification results.
- **SalaryHistory** – provides historical salary statistics based on previously collected offers.
- **StatisticsSalary** – calculates statistical salary metrics used by the estimation process.
- **SalaryEstimator** – estimates missing salary information using available salary data and historical statistics.
- **ProcessedCache** – tracks processed emails to prevent duplicate processing.
- **Orchestrator** – coordinates the entire processing pipeline.
- **Configuration** – manages application settings, filtering rules, and classification configuration.

The modular architecture allows individual components to be developed, tested, and modified independently.

## 3. Email Sources

The system collects job-offer data from email and web sources. Email messages and scraped records are converted into the common `JobOffer` structure before filtering and persistence.

```text
Email Sources
     |
     +-- RocketJobs
     +-- Pracuj.pl
     +-- LinkedIn
     +-- justjoin.it
     +-- theprotocol.it
     +-- Jooble
     |
     v
  Email Parser ------------------+
                                 |
Scrapers                         |
  |                              |
  +-- Pracuj scraper             |
  +-- LinkedIn scraper           |
  |                              |
  +------------------------------+
                 |
                 v
              JobOffer
```

Email folders and cache files are defined in `modules/email_sources.py`; scraper URLs are read from configuration. Each source may use a different structure, and its parser or adapter converts records into the standardized `JobOffer` model.

The `JobOffer` model provides a common interface for the rest of the application, regardless of the original email source.

Typical information extracted from an email includes:

- job title
- company
- location
- salary information, when available
- date
- source

After parsing, the original email format is no longer relevant to the subsequent processing stages. The normalized `JobOffer` is passed to filtering, classification, database storage, and salary estimation.

## 4. Database Structure

The main table is `Offers`, which stores the basic information about each job offer:

Title — the job offer title.

- id_offer - indywidual ID in database
- company — the company name.
- location — the location of the position.
- salary_min — the minimum gross salary offered for the position.
- salary_max — the maximum gross salary offered for the position.
- source — the source from which the offer was obtained.
- salary_status — indicates whether the salary comes from the original offer or was estimated.

The `JobDetails` table stores additional information generated during job classification:

- id_offer - indywidual ID in database
- clean_title — the cleaned version of the title from the `Offers` table.
- level — the seniority level assigned to the position.
- category — the job category assigned during classification.

The `Companies` table stores unique companies referenced by job offers. Company names are deduplicated to avoid storing the same company multiple times.

- id_company — unique identifier of the company in the database.
- company — unique company name.

table `Offers` - Stores the primary data extracted from job offers.

table `JobDetails` - Stores derived information generated by the classification process.

table `Companies` - Stores company-related information used to associate offers with companies.

## 5. Job Classification

Job classification provides two important pieces of information:

- Level
- Category

The level is classified based on the cleaned job title retrieved from the `Offers` table. The classification uses level keywords defined in JobClassifier.

- Senior
- Junior
- Intern
- Mid
- Manager

If a matching keyword is found, the corresponding level is assigned. If no level can be identified, the result is set to unknown.

The category is determined using the configured categories from `filter_keywords.json`. The classifier first uses keyword matching and scoring to identify the most relevant category. If the category can't be determined reliably, the classification is passed to AIService, which validates the job title against the available categories.

If neither the keyword-based classifier nor AIService can identify a valid category, the result is set to unknown.

```text
JobClassificationService

        │
        ▼

   JobClassifier

        │
        ├── Level → keyword matching from filter_keywords.json
        │
        └── Category → keyword scoring from filter_keywords.json
                          │
                          ├── match ────────────────┐
                          │                          │
                          └── no match → AIService  │
                                      │             │
                                      ▼             │
                               AI classification    │
                                      │             │
                                      └─────┬───────┘
                                            ▼
                                    JobClassification
                                            │
                                            ▼
                                        JobDetails
```

## 6. Salary Estimator

```text
JobClassificationService

        │
        ▼
process_salary_estimations()
        │

        ▼

get_job_contracts_for_salary_estimator()

        │

        ▼

JobContract + JobDetails

        │

        ├── salary_min_offer EXISTS
        │        OR
        │   salary_max_offer EXISTS
        │
        │        └──────────────────────► Skip estimation
        │
        └── salary_min_offer = NULL
            AND
            salary_max_offer = NULL
                    │
                    ▼
             level + category
                    │
                    ▼
             JobClassification
                    │
                    ▼
             SalaryEstimator
                    │
                    ▼
             salary_logic()
                    │
                    ▼
             SalaryHistory
                    │
                    ▼
             find_real_salary()
                    │
             company + title + date
                    │
                    │
              ± 60 days
                    │
               ┌────┴────┐
             FOUND    NOT FOUND
               │          │
               ▼          ▼
          Real Salary   get_salary()
                            │
                            ▼
                     Category + Level
                            │
                            ▼
                       Median Min / Max
                            │
                       ┌────┴────┐
                     FOUND    NOT FOUND
                       │          │
                       ▼          ▼
                 Statistical   Salary Rules
                    Salary     category + level
                                  │
                                  ▼
                             base + range
                       │          │
                       └────┬─────┘
                            │
                            ▼
                       Salary Min / Max
                            │
                            ▼
                 Update JobContract
                            │
                            ▼
                   Update Offers
                   salary_min / max
                   salary_status =
                       "estimated"

```

```text
SalaryEstimator

      │

      ▼

salary_logic()

      │

      ▼

find_real_salary()

company + title + date ± 60 days

      │

 ┌────┴────┐
FOUND    NOT FOUND
 │           │
 ▼           ▼
Real      get_salary()
Salary       │
             ▼
       Category + Level
             │
             ▼
        Median Min / Max
             │
        ┌────┴────┐
      FOUND     NOT FOUND
        │           │
        ▼           ▼
 Statistical   Salary Rules
    Salary     category + level
        │       base + range
        │           │
        └────┬──────┘
             │
             ▼
       Salary Min / Max
             │
             ▼
      JobContract update
             │
             ▼
        Offers update
             │
             ▼
    salary_status = estimated
```

## 7. End-to-End Processing Flow

The diagram below shows the email parsing and offer processing path. The current complete ETL flow, including scraper ingestion, duplicate checks, and orchestration order, follows it.

```text

Email Sources
     │
     ▼
EmailParser
     │
     ▼
Fetch unread emails
     │
     ▼
FileCache
     │
     ├── Already processed ───────────────► Skip
     │
     └── New email
             │
             ▼
        Extract HTML
             │
             ▼
        HTML → Text
             │
             ▼
        AIService
        parser_offers_api()
             │
             ▼
          JobOffer[]
             │
             ▼
        Parse email date
             │
             ▼
        SalaryParser
        extract_offer_text()
             │
             ▼
        offer_text
             │
             ▼
        Orchestrator
             │
             ▼
        FilterService
        should_save()
             │
        ┌────┴────┐
        │         │
    REJECTED    ACCEPTED
        │         │
        ▼         ▼
       END    save_offers()
                  │
                  ▼
                Offers
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
   Salary Processing   Classification
          │                │
          ▼                ▼
 validate_salary_api()  process_jobs()
          │                │
          ▼                ▼
    JobContract[]      JobDetails
          │                │
          ▼                │
 resolve_contract_type()   │
          │                │
          ▼                │
 normalize_salary()        │
          │                │
          ▼                │
    JobContracts           │
          │                │
          └────────┬───────┘
                   ▼
          Salary Estimation
                   │
                   ▼
   get_job_contracts_for_salary_estimator()
                   │
                   ▼
              JobContract
                   │
                   ├── Source salary exists ───────► Skip estimation
                   │
                   └── Source salary missing
                              │
                              ▼
                       SalaryEstimator
                              │
                              ▼
                        SalaryHistory
                              │
                    ┌─────────┴─────────┐
                    │                   │
             Real salary found     Not found
                    │                   │
                    ▼                   ▼
              Real Salary       Statistical Salary
                                      │
                                 ┌────┴────┐
                                 │         │
                              Found     Not found
                                 │         │
                                 ▼         ▼
                           Median Min/Max  Salary Rules
                                             │
                                             ▼
                                      Estimated Min/Max
                    │
                    └──────────────┬──────────────┘
                                   ▼
                           Update JobContract
                                   │
                                   ▼
                         Update Offer salary
                                   │
                                   ▼
                         Final Salary Selection
                                   │
                                   ▼
                         get_job_contracts()
                                   │
                                   ▼
                            JobContract[]
                                   │
                                   ▼
                        select_contract()
                                   │
                                   ▼
                          UoP > B2B > UZ
                                   │
                                   ▼
                         Selected Contract
                                   │
                                   ▼
                       get_salary_status()
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                 monthly       non-monthly     no source
                    │              │              │
                    ▼              ▼              ▼
                  offer      offer_calculate   estimated
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
                         Final Offers update
                                   │
                                   ▼
                              PostgreSQL
                                   │
                                   ▼
                                  END

```

### 7.1 Current Complete ETL Flow

The orchestrator first prepares the database and salary history, then processes offers from all configured sources. Classification and salary estimation run after source ingestion.

Duplicate detection is limited to offers with the same date, title, company, and source. Matching offers from another source or another date are kept as separate records. Offers without a date are not checked for duplicates.

```text
Orchestrator
     |
     +--> Create PostgreSQL schema
     +--> Update ended offer statuses
     +--> Load salary history
     |
     +--> Email parsers -----------+
     |                             |
     +--> Pracuj / LinkedIn scraper ---+
                                   |
                                   v
                         OfferSourceWorkflow
                                   |
                                   v
                           FilterService
                            /         \
                        reject       accept
                          |             |
                         skip     Same-source duplicate?
                                      /       \
                                    yes        no
                                     |          |
                                    skip   Set offer status
                                                |
                                                v
                                           Save Offer
                                          /          \
                                      email        scraper
                                        |              |
                               AI salary validation  Adapt record
                                        |              |
                               Contracts returned?     |
                                  /          \         |
                                yes            no      |
                                 |              |      |
                                 |       Empty UoP     |
                                 +--------------+------+
                                               v
                                  Normalize and save contracts
                                               |
                                               v
                                Classify missing JobDetails
                                               |
                                               v
                              Estimate missing source salaries
                                               |
                                               v
                              Collect offers with contracts
                                               |
                                               v
                                  Select UoP > B2B > UZ
                                               |
                                               v
                              Update final offer salary/status
                                               |
                                               v
                                          PostgreSQL
```

## 8. Configuration

The application uses configuration files to control filtering, job classification, salary estimation and other runtime parameters. This allows the system behavior to be modified without changing the application code.

### 8.1 Configuration Files

The main configuration files are:

- `filter_keywords.json` – keywords and phrases used for job offer filtering and classification and fallback salary ranges used when there is not enough historical salary data for a given category and seniority level.
- `.env` – environment-specific configuration and credentials where is Gemini API, login and password email.
- `config.py` / `AppConfig` – application configuration loader and access layer.

### 8.2 Job Filtering Configuration

`filter_keywords.json` contains rules used to identify and exclude irrelevant job offers.

The configuration includes:

- blocked job titles,
- skip phrases,
- irrelevant phrases,
- category-specific keywords,
- literal category mappings.

This configuration is loaded at application startup and used by the filtering
and classification services.

### 8.3 Salary Configuration

Salary estimation uses two data sources:

1. historical salary data collected from real job offers,
2. fallback salary rules defined in the configuration.

Historical data has priority. If sufficient historical data is available for a given category and seniority level, the estimator uses statistical values from `SalaryHistory`. Otherwise, predefined rules from `filter_keywords.json` are used.

Example salary rules:

```json
{
  "finance_accounting": {
    "Junior": {
      "range": 1200
    },
    "Mid": {
      "base": 7500,
      "range": 1800
    }
  }
}
```

### 8.4 AI Configuration

The AI classification service is configured with:

- Gemini model,
- JSON response format,
- Pydantic response schema,
- temperature,
- remote-call limits.

AI is primarily used for new or unclassified offers. Classification results are cached to reduce unnecessary API calls and API quota usage.

### 8.5 Runtime Configuration

```text
The application loads configuration during startup:

Application
    ↓
AppConfig
    ↓
Configuration files
    ↓
Filtering / Classification / Salary Estimation
```

Configuration is kept separate from business logic so that classification rules, salary parameters and filtering criteria can be updated independently of the application code.

## 9. Testing

The project uses unit tests and integration tests to verify individual components and interactions with the database.

### 9.1 Unit Tests

Unit tests verify individual components independently from the rest of the application.

- test_ai — verifies the response received from the Gemini API and validates the returned data using the expected Pydantic structure, including date, title, company, location, salary_min, and salary_max.

- test_classification — verifies job classification based on the keywords defined in filter_keywords.json and the logic implemented in job_classifier.py.

- test_filter_json — verifies the filtering rules defined in filter_keywords.json and checks that unexpected or unsupported values are handled correctly.

- test_filter_service — verifies that the filtering service correctly accepts valid job offers and rejects invalid or irrelevant offers.

- test_json — verifies that the application correctly reads and retrieves values from filter_keywords.json.

- test_orchestrator — verifies that the main application orchestrator correctly connects the individual processing modules.

- test_pydantic — verifies that JobOffer, implemented as a Pydantic BaseModel, correctly validates job offer data before it is stored in the database.

- test_salary_status — verifies that the salary status is correctly assigned depending on whether salary information comes from the original offer or is estimated.

- test_base_scraper — verifies record validation, JSON output, and avoiding duplicate scraper offers on the same day.

- test_email_parser — verifies that parsed email offers include their extracted salary text and email cache ID.

- test_linkedin_scraper — verifies LinkedIn card text extraction, page scrolling, saving new offers, and skipping offers already saved that day.

- test_salary_parser — verifies that salary text is associated with the matching offer and excludes neighboring offers.

- test_salary_processor_salary — verifies monthly and yearly salary normalization and salary status for missing, monthly, and hourly salary data.

- test_salary_processor_selection — verifies contract priority (UoP over B2B over UZ) and the empty contract list case.

- test_scraper — verifies Pracuj offer extraction with and without salary data and saving offers to JSON.

- test_scraper_record_to_contract — verifies conversion of scraper salary ranges and contract types, including missing or unsupported salary formats.

- test_update_status — verifies salary recovery from email or a previous offer and guards for missing offers, existing contracts, or unavailable salary data.

- test_validate_ai — verifies that AI salary validation converts an hourly salary response into a job contract.

- test_offer_source_workflow — unit tests for filtering, same-source duplicate handling, fallback contracts for email offers without validated salary data, and scraper contract processing without AI validation.

- test_job_classification_service — new unit tests for final contract salary normalization and selection, persistence of changed monthly values, and the no-selectable-contract case.

### 9.2 Integration Tests

Integration tests verify interactions between application components and the database.

- test_save_db — verifies that processed job offers are correctly saved to the test database.

- test_save_job_link — verifies that job offer links are correctly stored and associated with the corresponding offer in the database.

## 10. Operational Tools and Project Resources

### 10.1 Environment and Local Configuration

The runtime reads email credentials from `EMAIL`, `PASSWORD`, `EMAIL_HOST`, and `EMAIL_PORT`; `EMAIL_PORT` defaults to `993`. `KEY_API` supplies the Gemini API key. PostgreSQL uses `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`. The names and placeholder values are shown in `.env_template`.

The application loads `filter_keywords.json` and `scraper_urls.json` from the project root. Example versions are provided as `filter_keywords_example.json` and `scraper_urls_example.json`. The active JSON files are ignored by Git, so create or copy them locally before running the application. `filter_keywords.json` controls filtering, classification keywords, and salary rules; `scraper_urls.json` supplies URL lists to the Pracuj and LinkedIn scrapers.

### 10.2 Salary Recovery Utility

`backfill_offer_status.py` runs `SalaryRecovery` for a single offer ID:

```bash
uv run python backfill_offer_status.py <offer_id>
```

The utility is for offers whose source maps to a configured email folder. It searches that folder on the saved offer's date, checks messages for the offer title and company, then asks `AIService` to validate salary information. If it cannot recover salary from email, it tries the latest matching offer with saved salary. The recovery stops when the offer does not exist or a contract already contains salary values; a placeholder UoP contract can be created when no salary is found.

### 10.3 Database Maintenance and SQL Resources

The scripts in `database/db_operations/` are manual PostgreSQL maintenance utilities:

- `migrate_status.py` fills missing offer salary statuses from the salary columns.
- `migration_db.py` creates `JobDetails` rows from existing offers.
- `migration_salary.py` creates `JobContracts` rows from existing offer salary columns.

The two row-copying scripts insert records for existing offers and do not check for duplicates. Review the target database before running them again.

The root SQL files are also manual resources and are not applied by `orchestrator.py`:

- `queries.sql` contains diagnostic and analysis queries for salary status, sources, companies, and offer history.
- `views.sql` defines reporting views, including total offers and normalized locations. The location view currently limits data to dates from `2026-05-01` onward.
- `trigger.sql` defines a PostgreSQL trigger that normalizes selected contract type labels during insert or update.

### 10.4 Scraper Artifacts and Logging

The Pracuj and LinkedIn scrapers write records to `filter_pracuj_offers.json` and `filter_linkedin_offers.json`. `BaseScraper` validates records, adds the scrape date, and skips records with a previously seen offer ID or URL for that date. The email parsers keep processed message IDs in per-source text files under `mail_records/`. These generated files are local runtime state and are ignored by Git.

LinkedIn scraping uses a visible Playwright browser and the persistent profile directory `linkedni_profile`; the Pracuj scraper also launches a visible browser. The orchestrator writes runtime logs to `etl.log`.

`linkedin_login.py` opens the LinkedIn login page in the same persistent profile directory, allowing a user to sign in before starting the LinkedIn scraper.

### 10.5 Continuous Integration

`.github/workflows/ci.yml` runs on pull requests. It sets up Python `3.14.4`, installs dependencies with `uv sync`, copies the example JSON files into the active configuration filenames, runs `ruff check .`, and runs `pytest`. The tests under `integration_tests/` use mocked database connections; the CI job does not provision or verify a live PostgreSQL server.

The current database-operation test files are `integration_tests/test_offers_db.py` and `integration_tests/test_save_offer_2_contracts.py`.

### 10.6 Filtering, Classification, and Offer Status Rules

Before saving, `FilterService` removes configured legal-form suffixes from the company name. It rejects titles shorter than three characters or companies shorter than two characters, the literal value `null`, and configured bad title markers. A title must also contain a configured job phrase and must not contain an excluded phrase; configured junk phrases are removed before this check.

Seniority classification checks configured keywords in this order: senior, junior, intern, mid, and manager. Category classification scores matching keywords (single-word matches score 1, two-word matches 5, and phrases of three or more words score 10). When there is no keyword match, it asks AI to select from the configured literal categories. Classification by title is reused from the database when an existing category is available, and category results are cached in memory during the run.

An offer without a date receives status `process`. With a date, it receives `new` when no matching title/company history exists or the latest matching offer is at least 30 days older; otherwise it receives `process`. During the next ETL run, offers are grouped into posting cycles by title and company. A cycle is marked `ended` when its last offer date is at least 30 days old; a gap of at least 30 days starts a new cycle.

### 10.7 Salary Normalization and Status Values

`SalaryProcessor` accepts hourly, daily, weekly, monthly, and yearly source periods. It normalizes them to monthly values using 168 working hours per month, 21 working days per month, 52 weeks per year, and 12 months per year. If one source bound is missing, it copies the available bound to the missing side; if no period is supplied, it assumes monthly. When a normalized minimum is below 500, both normalized monthly bounds are cleared.

The salary status is `estimated` when both source salary bounds are missing, `offer` for a monthly source salary, and `offer_calculate` for a source salary in another period. Final contract selection follows `UoP`, `B2B`, and `UZ` priority, returning the first matching contract of the highest available type.
