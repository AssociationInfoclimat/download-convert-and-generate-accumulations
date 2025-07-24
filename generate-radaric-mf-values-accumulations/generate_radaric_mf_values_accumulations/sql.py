import os
from typing import Any, Optional

from sqlalchemy import Connection, CursorResult, Engine, create_engine, text

HOST = os.environ["DB_HOST"]
USER = os.environ["DB_USER"]
PASSWORD = os.environ["DB_PASSWORD"]


def get_engine(database: str = "V5") -> Engine:
    return create_engine(f"mysql+mysqlconnector://{USER}:{PASSWORD}@{HOST}/{database}")


def get_sql_connection(database: str = "V5") -> Connection:
    engine = get_engine(database)
    return engine.connect()


def execute_sql(
    connection: Connection, statement: str, values: Optional[dict[str, Any]] = None
) -> CursorResult[Any]:
    return connection.execute(text(statement), values)


def execute_and_commit_sql(
    connection: Connection, statement: str, values: dict[str, Any]
) -> None:
    execute_sql(connection, statement, values)
    connection.commit()
