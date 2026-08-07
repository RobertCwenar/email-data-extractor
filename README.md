# EMAIL DATA EXTRACTION

## Introduction

Job Data Extractor is an ETL pipeline designed to automatically extract, transform, and load job offer data from different sources.
The main goal of the project is to automate the process of collecting data from emails, web pages, and other sources by using an ETL pipeline that extracts, transforms, and loads data into a structured database.

## About

Email parsing pipeline for processing and analyzing incoming messages. The project focuses on extracting structured data from emails, with a specific use case of parsing job offers from WP (Wirtualna Polska). It includes cleaning email content, extracting key information, and organizing data for further analysis.

## Technologies

- Python
- SQLite
- SQL
- AI API Integration
- Power BI (planned)

## Features

- Extracts job offers from email sources using IMAP
- Parses unstructured email content
- Cleans and transforms extracted data
- Validates data using Pydantic models
- Stores processed data in SQLite database
- Includes automated tests

## Architecture

```text
Emails
  ↓
Email Parser
  ↓
JobOffer Model (Pydantic)
  ↓
AI Classification
  ↓
Filters
  ↓
SQLite Database
```

## Usage and Installation

### 1. Clone the repository

```bash
git clone: [https://github.com/RobertCwenar/email-data-extractor]
cd email-data-extractor
```

### 2. Install dependencies

Make sure you have Python installed, then install the project dependencies:

```text
• uv sync
or:
• pip install -r requirements.txt
```

### 3. Configure environment variables

#### Create a .env file and add required configuration values, for example

- EMAIL_HOST=your_email_host
- EMAIL_USER=your_email
- EMAIL_PASSWORD=your_password

### 4. Run the application

#### Start the parser with

```bash
uv run python orchestrator.py
```

The application connects to the configured mailbox, extracts job offers, processes the data, and saves the results.

### 5. Run tests

#### To run the test suite

```bash
uv run pytest
```

### 6. Code quality checks

#### Run linting and formatting

- uv run ruff check .
- uv run ruff format .

#### Output

After successful execution, processed job offers are saved to the configured.

## Project Structure

```text
/email-data-extractor
│
│
├── /database
│    ├── init_database.py
│    ├── migration_db.py
│
├── /core
│   ├── __init__.py
│   ├── base_parser.py
│
├── /modules
│   ├── __init__.py
│   ├── ai_service.py
│   ├── db_save.py
│   ├── filter_service.py
│   ├── processed_cache.py
│
├── /parsers
│   ├── __init__.py
│   ├── email_parser.py
│
├── /tests
│   ├── test_ai.py
│   ├── test_filter_service.py
│   ├── test_filterjson.py
│   ├── test_json.py
│   ├── test_orchestrator.py
│   ├── test_pydantic.py
│   ├── test_save_db.py
│   ├── test_save_job_link.py
│
├── config.py
├── offer.py
├── orchestrator.py
├── pyproject.toml
├──.pre-commit-config.yaml
├──.python-version
├── LICENSE
├── README.md
├── uv.lock
└── .gitignore
```

## Roadmap
