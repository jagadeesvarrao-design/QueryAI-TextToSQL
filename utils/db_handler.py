"""
db_handler.py — Thin compatibility wrapper.
All real logic is now in connection_manager.py.
This file keeps backwards-compat for the demo (hospital SQLite) mode only.
"""
import os
import pandas as pd
from utils.connection_manager import (
    build_engine,
    extract_schema_string,
    extract_schema_dict,
    get_table_names_from_engine,
    get_table_preview_from_engine,
    run_query_on_engine,
    ConnectionConfig,
)

# Demo database path (used by setup_db.py)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "hospital.db")

# Build the demo engine once at import time (lazy)
_demo_engine = None


def _get_demo_engine():
    global _demo_engine
    if _demo_engine is None:
        cfg = ConnectionConfig(db_type="🏥 Demo (Hospital SQLite)")
        engine, err = build_engine(cfg)
        if err:
            raise RuntimeError(f"Could not open demo DB: {err}")
        _demo_engine = engine
    return _demo_engine


# ── Public API (used by app.py for demo mode) ──────────────────────────────────

def get_schema() -> str:
    return extract_schema_string(_get_demo_engine())


def get_full_schema_dict() -> dict:
    return extract_schema_dict(_get_demo_engine())


def get_table_names() -> list:
    return get_table_names_from_engine(_get_demo_engine())


def get_table_preview(table_name: str, limit: int = 5) -> pd.DataFrame:
    return get_table_preview_from_engine(_get_demo_engine(), table_name, limit)


def run_query(sql: str) -> tuple:
    return run_query_on_engine(_get_demo_engine(), sql)
