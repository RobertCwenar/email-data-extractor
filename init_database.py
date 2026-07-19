import sqlite3


# Create new dataframe with new offers
def init_db(db_name="new_offers.db"):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Offers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            salary_min TEXT,
            salary_max TEXT,
            date TEXT,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()
