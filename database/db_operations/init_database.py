import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


# Create new dataframe with new offers
def init_db():
    with psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    ) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Companies (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            company TEXT UNIQUE NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Offers (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            salary_min DOUBLE PRECISION,
            salary_max DOUBLE PRECISION,
            date TEXT,
            source TEXT,
            salary_status TEXT,
            offer_status TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS JobDetails (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            offer_id INTEGER NOT NULL,
            clean_title TEXT,
            level TEXT,
            category TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS JobContracts (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            offer_id INTEGER NOT NULL,
            contract_type TEXT,
            salary_currency TEXT,
            salary_period TEXT,
            salary_min_offer DOUBLE PRECISION,
            salary_max_offer DOUBLE PRECISION,
            salary_min_monthly DOUBLE PRECISION,
            salary_max_monthly DOUBLE PRECISION,
            FOREIGN KEY (offer_id) REFERENCES Offers(id)
        )
        """)
