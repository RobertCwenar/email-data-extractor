### EMAIL DATA EXTRACTION

## Introduction

Job Data Extractor is an ETL pipeline designed to automatically extract, transform, and load job offer data from different sources.
The main goal of the project is to automate the process of collecting data from emails, web pages, and other sources by using an ETL pipeline that extracts, transforms, and loads data into a structured database.

## About

Email parsing pipeline for processing and analyzing incoming messages. The project focuses on extracting structured data from emails, with a specific use case of parsing job offers from WP (Wirtualna Polska). It includes cleaning email content, extracting key information, and organizing data for further analysis.

## Usage and Installation

# 1. Clone the repository

git clone: https://github.com/RobertCwenar/email-data-extractor
cd email-data-extractor

# 2. Install dependencies

Make sure you have Python installed, then install the project dependencies:
• uv sync
or:
• pip install -r requirements.txt

# 3.Configure environment variables

Create a .env file and add required configuration values, for example:
• EMAIL_HOST=your_email_host
• EMAIL_USER=your_email
• EMAIL_PASSWORD=your_password

# 4.Run the application

Start the parser with:
uv run python main.py
The application connects to the configured mailbox, extracts job offers, processes the data, and saves the results.

# 5.Run tests

To run the test suite:
• uv run pytest

# 6.Code quality checks

Run linting and formatting:
• uv run ruff check .
• uv run ruff format .

Output
After successful execution, processed job offers are saved to the configured.

## Features

- Extracts job offers from email sources using IMAP
- Parses unstructured email content
- Cleans and transforms extracted data
- Validates data using Pydantic models
- Stores processed data in SQLite database
- Includes automated tests

## Project Structure
