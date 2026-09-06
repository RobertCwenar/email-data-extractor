# Technical Documentation

## 1. System Overview

The main and most important part of the workflow is retrieving job offer data from email. The process starts by logging into the WP.pl email account and reading messages from the appropriate folders.

After processing, the system saves the IDs of all processed emails in `mail_records`. This prevents the same email from being processed a second time. If an email is untracked but its ID is already saved in `mail_records`, it can be safely skipped. The individual ID stored in the file improves the email processing flow and enables individual monitoring of processed emails in the project.

The extracted email content is then processed and transformed into structured job offer data. Pydantic is used to validate the structure of the data, while AI-based classification is used to determine additional information about the job offer.

The application uses the `filter_keywords.json` configuration file to define filtering and classification rules. Based on these rules, irrelevant offers can be filtered out and relevant data can be assigned to the appropriate fields. When a category cannot be determined using the keywords defined in `filter_keywords.json`, the system uses AI classification to determine the appropriate category.

The processed data is stored in an SQLite database, with `Offers` serving as the main table. Additional important tables include `JobDetails` and `Companies`.

```text
Email
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
SQLite
```

## 2. System Architecture

The system is designed as a modular ETL pipeline for processing job offers from multiple sources.

### 2.1 Data Flow

```text
Email
  ↓
EmailParser
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
SQLite
```

### 2.2 Main Components

- **EmailParser** – extracts job offer data from emails.
- **FilterService** – filters unwanted offers using configured rules.
- **AIService** – uses AI for structured data extraction and job offer analysis.
- **Pydantic Models** – validate and normalize application data.
- **Database Layer** – manages SQLite database initialization, migrations, persistence, and data access.
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

The system uses incoming email messages as the primary source of job-offer data. Emails are received from multiple job platforms and processed into a common JobOffer structure.

```text
Email Sources
     │
     ├── RocketJobs.pl
     │
     ├── LinkedIn
     │
     ├── Pracuj.pl
     │
     └── WP.pl
            │
            ▼
       Email Parser
            │
            ▼
         JobOffer
```

Each source may use a different email structure and formatting. The parsing layer is responsible for extracting the relevant information and converting it into a standardized `JobOffer` object.

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

The complete processing pipeline combines email extraction, data validation, filtering, classification, and salary estimation into a single workflow.

```text

E## 7. End-to-End Processing Flow

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
                                SQLite
                                   │
                                   ▼
                                  END

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

### 9.2 Integration Tests

Integration tests verify interactions between application components and the database.

- test_save_db — verifies that processed job offers are correctly saved to the test database.

- test_save_job_link — verifies that job offer links are correctly stored and associated with the corresponding offer in the database.
