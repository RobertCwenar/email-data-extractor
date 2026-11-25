import logging
import os
from contextlib import AbstractContextManager
from typing import Any

from psycopg import Connection
from psycopg.rows import TupleRow
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        database_url = os.getenv("DATABASE_URL", "").strip()

        if database_url:
            conninfo = database_url
            connection_kwargs: dict[str, Any] = {"connect_timeout": 10}
        else:
            conninfo = ""
            connection_kwargs = {
                "host": os.getenv("POSTGRES_HOST"),
                "port": os.getenv("POSTGRES_PORT", "5432"),
                "dbname": os.getenv("POSTGRES_DB"),
                "user": os.getenv("POSTGRES_USER"),
                "password": os.getenv("POSTGRES_PASSWORD"),
                "sslmode": os.getenv("POSTGRES_SSLMODE", "require"),
                "connect_timeout": 10,
            }

        logger.info("Opening PostgreSQL connection pool")
        self._pool = ConnectionPool(
            conninfo=conninfo,
            kwargs=connection_kwargs,
            min_size=1,
            max_size=3,
            timeout=10,
            max_lifetime=600,
            max_idle=60,
            reconnect_timeout=20,
            name="job-etl",
            open=False,
        )
        self._pool.open()
        self._pool.wait(timeout=15)
        logger.info("PostgreSQL connection pool is ready")

    def _connect(self) -> AbstractContextManager[Connection[TupleRow]]:
        return self._pool.connection(timeout=10)

    def close(self) -> None:
        self._pool.close()
