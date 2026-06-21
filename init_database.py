import sqlite3

# Create new dataframe with new offers
def init_db(db_name='new_offers.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Offers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            salary TEXT,
            date TEXT,
            source TEXT
        )
    ''')
    conn.commit()
    conn.close()