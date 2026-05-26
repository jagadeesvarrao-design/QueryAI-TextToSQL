"""
connection_manager.py — Universal database connection manager using SQLAlchemy.
Supports: MySQL, PostgreSQL, MSSQL, Oracle, SQLite (file), CSV (in-memory SQLite).
"""
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text, inspect


# ─── DB Engine Configs ─────────────────────────────────────────────────────────

DB_CONFIGS = {
    "🏥 Demo (Hospital SQLite)": {
        "driver": "sqlite_demo",
        "default_port": None,
        "icon": "🏥",
        "color": "#00C9A7",
        "description": "Built-in hospital database. No setup needed!",
    },
    "📄 CSV Upload": {
        "driver": "csv",
        "default_port": None,
        "icon": "📄",
        "color": "#F6AD55",
        "description": "Upload any CSV file and query it instantly.",
    },
    "🐬 MySQL": {
        "driver": "mysql+pymysql",
        "default_port": 3306,
        "icon": "🐬",
        "color": "#00758F",
        "description": "Connect to your MySQL server.",
        "url_template": "mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
    },
    "🐘 PostgreSQL": {
        "driver": "postgresql+psycopg2",
        "default_port": 5432,
        "icon": "🐘",
        "color": "#336791",
        "description": "Connect to your PostgreSQL server.",
        "url_template": "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
    },
    "🪟 Microsoft SQL Server": {
        "driver": "mssql+pymssql",
        "default_port": 1433,
        "icon": "🪟",
        "color": "#CC2927",
        "description": "Connect to your Microsoft SQL Server.",
        "url_template": "mssql+pymssql://{user}:{password}@{host}:{port}/{database}",
    },
    "🔴 Oracle SQL": {
        "driver": "oracle+oracledb",
        "default_port": 1521,
        "icon": "🔴",
        "color": "#F80000",
        "description": "Connect to your Oracle database.",
        "url_template": "oracle+oracledb://{user}:{password}@{host}:{port}/{database}",
    },
    "📁 SQLite (File)": {
        "driver": "sqlite",
        "default_port": None,
        "icon": "📁",
        "color": "#7B68EE",
        "description": "Connect to a local .db / .sqlite file.",
    },
}


@dataclass
class ConnectionConfig:
    db_type: str                        # Key from DB_CONFIGS
    host: str = ""
    port: int = 0
    database: str = ""
    username: str = ""
    password: str = ""
    sqlite_path: str = ""               # For SQLite file mode
    csv_dataframes: dict = field(default_factory=dict)   # {table_name: df} for CSV mode
    extra_params: str = ""              # e.g. "charset=utf8" or "TrustServerCertificate=yes"


# ─── Connection Builder ────────────────────────────────────────────────────────

def build_engine(config: ConnectionConfig):
    """
    Build a SQLAlchemy engine from a ConnectionConfig.
    Returns (engine, error_string).
    """
    db_type = config.db_type
    driver_info = DB_CONFIGS.get(db_type, {})
    driver = driver_info.get("driver", "")

    try:
        if db_type == "🏥 Demo (Hospital SQLite)":
            import os
            demo_db = os.path.join(
                os.path.dirname(__file__), "..", "database", "hospital.db"
            )
            engine = create_engine(f"sqlite:///{demo_db}", connect_args={"check_same_thread": False})

        elif db_type == "📄 CSV Upload":
            # CSV data is already loaded into in-memory SQLite externally
            # We return None — the caller handles CSV via pandas directly
            return None, ""

        elif db_type == "📁 SQLite (File)":
            if not config.sqlite_path:
                return None, "Please provide the SQLite file path."
            engine = create_engine(
                f"sqlite:///{config.sqlite_path}",
                connect_args={"check_same_thread": False}
            )

        else:
            # Build URL for network databases
            url_template = driver_info.get("url_template", "")
            if not url_template:
                return None, f"URL template not found for {db_type}"

            # Encode password to handle special characters
            from urllib.parse import quote_plus
            safe_password = quote_plus(config.password)

            url = url_template.format(
                user=config.username,
                password=safe_password,
                host=config.host,
                port=config.port,
                database=config.database,
            )

            # Append advanced connection parameters if specified
            if config.extra_params:
                clean_params = config.extra_params.lstrip("?").lstrip("&")
                if "?" in url:
                    url = f"{url}&{clean_params}"
                else:
                    url = f"{url}?{clean_params}"

            engine = create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=5)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return engine, ""

    except Exception as e:
        return None, str(e)


# ─── Schema Extraction ─────────────────────────────────────────────────────────

def extract_schema_string(engine, csv_tables: dict = None) -> str:
    """
    Extract schema as a string for Gemini prompt injection.
    Supports both SQLAlchemy engines and CSV (dict of DataFrames).
    """
    if csv_tables:
        return _csv_schema_string(csv_tables)

    if engine is None:
        return ""

    try:
        inspector = inspect(engine)
        schema_parts = []

        # Handle schema-aware databases (PostgreSQL, MSSQL, Oracle)
        try:
            tables = inspector.get_table_names(schema=None)
        except Exception:
            tables = inspector.get_table_names()

        for table in tables[:50]:  # Cap at 50 tables
            try:
                columns = inspector.get_columns(table)
                col_defs = ", ".join(
                    f"{col['name']} ({str(col['type'])})" for col in columns
                )
                part = f"Table: {table}\n  Columns: {col_defs}"

                # Row count (skip if too slow on large DBs)
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {_quote_table(table, engine)}"))
                        count = result.scalar()
                    part += f"\n  Row count: {count}"
                except Exception:
                    pass

                schema_parts.append(part)
            except Exception:
                continue

        return "\n\n".join(schema_parts)

    except Exception as e:
        return f"Schema extraction error: {str(e)}"


def extract_schema_dict(engine, csv_tables: dict = None) -> dict:
    """
    Extract schema as {table_name: [(col_name, col_type), ...]} for sidebar rendering.
    """
    if csv_tables:
        return {
            table: [(col, str(df[col].dtype)) for col in df.columns]
            for table, df in csv_tables.items()
        }

    if engine is None:
        return {}

    try:
        inspector = inspect(engine)
        try:
            tables = inspector.get_table_names(schema=None)
        except Exception:
            tables = inspector.get_table_names()

        schema = {}
        for table in tables[:50]:
            try:
                columns = inspector.get_columns(table)
                schema[table] = [(col["name"], str(col["type"])) for col in columns]
            except Exception:
                schema[table] = []
        return schema
    except Exception:
        return {}


def get_table_names_from_engine(engine, csv_tables: dict = None) -> list:
    """Return list of table names."""
    if csv_tables:
        return list(csv_tables.keys())
    if engine is None:
        return []
    try:
        inspector = inspect(engine)
        try:
            return inspector.get_table_names(schema=None)[:50]
        except Exception:
            return inspector.get_table_names()[:50]
    except Exception:
        return []


def get_table_preview_from_engine(engine, table_name: str, limit: int = 5,
                                   csv_tables: dict = None) -> pd.DataFrame:
    """Return first N rows of a table."""
    if csv_tables and table_name in csv_tables:
        return csv_tables[table_name].head(limit)
    if engine is None:
        return pd.DataFrame()
    try:
        with engine.connect() as conn:
            quoted = _quote_table(table_name, engine)
            df = pd.read_sql(text(f"SELECT * FROM {quoted} LIMIT {limit}"), conn)
        return df
    except Exception:
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(f"SELECT TOP {limit} * FROM [{table_name}]"), conn)
            return df
        except Exception:
            return pd.DataFrame()


def run_query_on_engine(engine, sql: str, csv_tables: dict = None) -> tuple:
    """
    Execute SQL and return (DataFrame, error_string).
    For CSV mode, execute against in-memory SQLite.
    """
    if csv_tables:
        return _run_csv_query(sql, csv_tables)

    if engine is None:
        return pd.DataFrame(), "No database connected."

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        return df, ""
    except Exception as e:
        return pd.DataFrame(), str(e)


# ─── CSV Helpers ───────────────────────────────────────────────────────────────

def _csv_schema_string(csv_tables: dict) -> str:
    parts = []
    for table_name, df in csv_tables.items():
        col_defs = ", ".join(
            f"{col} ({str(df[col].dtype)})" for col in df.columns
        )
        parts.append(
            f"Table: {table_name}\n  Columns: {col_defs}\n  Row count: {len(df)}"
        )
    return "\n\n".join(parts)


def _run_csv_query(sql: str, csv_tables: dict) -> tuple:
    """Load CSV DataFrames into an in-memory SQLite and run SQL against them."""
    try:
        mem_engine = create_engine("sqlite:///:memory:")
        with mem_engine.connect() as conn:
            for table_name, df in csv_tables.items():
                df.to_sql(table_name, conn, if_exists="replace", index=False)
            result = pd.read_sql(text(sql), conn)
        return result, ""
    except Exception as e:
        return pd.DataFrame(), str(e)


# ─── Utility ──────────────────────────────────────────────────────────────────

def _quote_table(table_name: str, engine) -> str:
    """Quote table name appropriately for the dialect."""
    dialect = engine.dialect.name
    if dialect == "mssql":
        return f"[{table_name}]"
    elif dialect in ("mysql", "sqlite"):
        return f"`{table_name}`"
    else:
        return f'"{table_name}"'


def get_dialect_name(engine) -> str:
    """Return human-readable dialect name."""
    if engine is None:
        return "Unknown"
    return engine.dialect.name.upper()
