import sqlite3


# Database class for saving job offers and related data to SQLite database
class Database:
    def __init__(self, db_name: str = "new_offers.db"):
        self.db_name = db_name

    def _connect(self):
        return sqlite3.connect(self.db_name, timeout=40)
