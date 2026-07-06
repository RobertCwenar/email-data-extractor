import sqlite3

import pandas as pd


# Migrate data from Excel to SQLite database
def migrate_db():
    conn = sqlite3.connect("new_offers.db")

    sources = {"Pracuj.pl": "Pracuj.pl", "LinkedIn": "Linkedin"}
    for sheet_neme, source_name in sources.items():
        try:
            df = pd.read_excel("new_offers.xlsx", sheet_name=sheet_neme)

            df["source"] = source_name
            df.to_sql("Offers", conn, if_exists="append", index=False)
            print(f"Add data from sheet: {sheet_neme}")

        except Exception:
            print("Failed import {sheet_name}: {e}")

    conn.close()
    print("Completed Migration!")


migrate_db()
