import os

import psycopg
from psycopg import Connection
from psycopg.rows import TupleRow


class Database:
    def _connect(self) -> Connection[TupleRow]:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if database_url:
            return psycopg.connect(database_url)

        return psycopg.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
        )
