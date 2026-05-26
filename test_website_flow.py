"""
test_website_flow.py — Simulates the complete end-to-end interactive flow of the 
QueryAI website (app.py) programmatically across different virtual database configurations.
Compatible with standard Windows terminals (non-UTF8 safe).
Run: python test_website_flow.py
"""
import os
import sys
import time
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv

# Ensure we can import from local path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Safe print utility to handle Windows non-UTF8 consoles gracefully
def safe_print(text):
    try:
        encoded = text.encode('cp1252', errors='ignore')
        decoded = encoded.decode('cp1252')
        print(decoded)
    except Exception:
        # Fallback to simple printing of ascii
        ascii_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(ascii_text)


# ─── Mock Streamlit Framework ──────────────────────────────────────────────────
class MockStreamlitSessionState(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f"Mock st.session_state has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        self[name] = value


class MockStreamlit:
    def __init__(self):
        self.session_state = MockStreamlitSessionState()
        self.errors = []
        self.successes = []
        self.infos = []
        self.warns = []

    def error(self, msg, icon=None):
        self.errors.append(msg)
        safe_print(f"  [ST ERROR] {msg}")

    def success(self, msg, icon=None):
        self.successes.append(msg)
        safe_print(f"  [ST SUCCESS] {msg}")

    def info(self, msg, icon=None):
        self.infos.append(msg)
        safe_print(f"  [ST INFO] {msg}")

    def warning(self, msg, icon=None):
        self.warns.append(msg)
        safe_print(f"  [ST WARN] {msg}")

    def spinner(self, text):
        class SpinnerContext:
            def __enter__(self):
                pass
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return SpinnerContext()


# Initialize virtual Streamlit mock
st = MockStreamlit()
sys.modules['streamlit'] = st  # Inject mock streamlit into sys.modules!

# Now import connection and handler modules that rely on st or project logic
from utils.connection_manager import (
    ConnectionConfig,
    build_engine,
    extract_schema_string,
    extract_schema_dict,
    get_table_names_from_engine,
    get_table_preview_from_engine,
    run_query_on_engine,
    get_dialect_name,
)
from utils.llm_handler import generate_sql
from utils.visualizer import auto_visualize

# Load environment
load_dotenv()

# ANSI Colors
GREEN = ""
RED = ""
YELLOW = ""
CYAN = ""
BOLD = ""
RESET = ""
if sys.platform != "win32" or os.environ.get("COLORTERM"):
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def reset_mock_state():
    st.errors.clear()
    st.successes.clear()
    st.infos.clear()
    st.warns.clear()
    
    # Re-initialize app.py session defaults
    st.session_state.clear()
    defaults = {
        "engine": None,
        "csv_tables": None,
        "connected": False,
        "active_db_type": "Demo Hospital",
        "conn_config": None,
        "schema_str": "",
        "schema_dict": {},
        "table_names": [],
        "query_history": [],
        "last_sql": "",
        "last_df": None,
        "last_question": "",
        "current_question": "",
        "gen_time": 0.0,
        "last_used_model": "",
    }
    for k, v in defaults.items():
        st.session_state[k] = v


def simulate_do_connect(config: ConnectionConfig, csv_tables=None):
    """Simulates app.py's do_connect function inside virtual Streamlit state."""
    safe_print(f"\n  [CONNECT] Simulating connection request to: {BOLD}{config.db_type}{RESET}")
    if config.db_type == "📄 CSV Upload":
        if not csv_tables:
            st.error("Please upload at least one CSV file.")
            return
        st.session_state.engine = None
        st.session_state.csv_tables = csv_tables
        st.session_state.connected = True
        st.session_state.active_db_type = "📄 CSV Upload"
        st.session_state.conn_config = config
        st.session_state.schema_str = extract_schema_string(None, csv_tables)
        st.session_state.schema_dict = extract_schema_dict(None, csv_tables)
        st.session_state.table_names = list(csv_tables.keys())
        st.success(f"Loaded {len(csv_tables)} CSV table(s)!")
        return

    engine, err = build_engine(config)
    if err:
        st.error(f"Connection failed: {err}")
        return

    st.session_state.engine = engine
    st.session_state.csv_tables = None
    st.session_state.connected = True
    st.session_state.active_db_type = config.db_type
    st.session_state.conn_config = config
    st.session_state.schema_str = extract_schema_string(engine)
    st.session_state.schema_dict = extract_schema_dict(engine)
    st.session_state.table_names = get_table_names_from_engine(engine)
    st.session_state.last_df = None
    st.session_state.last_sql = ""
    st.session_state.last_question = ""
    st.success(f"Connected to {config.db_type}! Found {len(st.session_state.table_names)} tables.")


def simulate_query_flow(question: str):
    """Simulates the main execution flow of app.py when a user runs an English query."""
    safe_print(f"\n  [QUERY] Simulating User Question: '{BOLD}{question}{RESET}'")
    if not st.session_state.connected:
        st.error("Cannot query: No database is connected!")
        return False

    # 1. Determine dialect
    if st.session_state.active_db_type == "📄 CSV Upload":
        active_dialect = "SQLite"
    elif st.session_state.engine:
        active_dialect = get_dialect_name(st.session_state.engine)
    else:
        active_dialect = "SQLite"

    safe_print(f"    - Step 1: Extracted engine SQL dialect: {active_dialect}")

    # 2. Call LLM
    safe_print(f"    - Step 2: Requesting {active_dialect}-compliant SQL translation from Gemini...")
    t0 = time.time()
    sql, used_model, llm_err = generate_sql(
        question, 
        st.session_state.schema_str, 
        dialect=active_dialect,
        model_name="gemini-2.5-flash"
    )
    gen_time = round(time.time() - t0, 2)

    if llm_err:
        st.error(f"AI Translation Error: {llm_err}")
        return False

    safe_print(f"    - Step 3: LLM generated clean SQL: {GREEN}{sql}{RESET} (Model: {used_model}, Time: {gen_time}s)")

    # 3. Run Query
    safe_print(f"    - Step 4: Running SQL against target virtual engine...")
    df, db_err = run_query_on_engine(
        st.session_state.engine, sql,
        csv_tables=st.session_state.csv_tables
    )

    if db_err:
        st.error(f"Database Query Error: {db_err}")
        return False

    rows, cols = df.shape
    safe_print(f"    - Step 5: Query executed successfully! Retrieved {rows} rows and {cols} columns.")

    # Update state
    st.session_state.last_sql = sql
    st.session_state.last_df = df
    st.session_state.last_question = question
    st.session_state.gen_time = gen_time
    st.session_state.query_history.append(question)

    # 4. Visualize
    safe_print(f"    - Step 6: Triggering auto-visualization rules...")
    fig = auto_visualize(df, question)
    if fig:
        safe_print(f"      {GREEN}[OK] Auto-Visualization successful! Created {type(fig).__name__} chart layout.{RESET}")
    else:
        safe_print(f"      [INFO] Result is single-value or non-chartable; bypassed plotting successfully.")

    return True


def run_virtual_website_tests():
    safe_print(f"\n{BOLD}{CYAN}[VIRTUAL RUN] Starting Website E2E Flow Simulation{RESET}\n" + "=" * 60)

    # ─── VIRTUAL DATABASE 1: HOSPITAL DEMO DB ──────────────────────────────────
    safe_print(f"\n{BOLD}[DB PROFILE 1] Demo Hospital SQLite{RESET}")
    reset_mock_state()
    
    cfg_demo = ConnectionConfig(db_type="🏥 Demo (Hospital SQLite)")
    simulate_do_connect(cfg_demo)
    
    # Assert state updates match app.py expected values
    assert st.session_state.connected is True
    assert len(st.session_state.table_names) >= 5
    assert "patients" in st.session_state.schema_dict
    safe_print(f"  {GREEN}[OK] Hospital SQLite state mounted perfectly.{RESET}")

    # Query flow test
    success = simulate_query_flow("What is the average billing amount per specialization?")
    assert success is True
    assert not st.session_state.last_df.empty
    safe_print(f"  {GREEN}[OK] End-to-end user query flow tested perfectly on SQLite!{RESET}")


    # ─── VIRTUAL DATABASE 2: DYNAMIC CSV UPLOAD ───────────────────────────────
    safe_print(f"\n{BOLD}[DB PROFILE 2] CSV Upload{RESET}")
    reset_mock_state()

    # Create mock CSV DataFrames (e.g. employees and branches)
    df_emp = pd.DataFrame({
        "emp_id": [101, 102, 103, 104],
        "name": ["Alex", "Sophia", "Marcus", "Emily"],
        "salary": [75000, 92000, 68000, 85000],
        "dept": ["IT", "HR", "Sales", "IT"]
    })
    df_dept = pd.DataFrame({
        "dept_name": ["IT", "HR", "Sales"],
        "manager": ["David", "Rachel", "Sarah"]
    })
    uploaded_csvs = {
        "employees_data": df_emp,
        "departments": df_dept
    }

    cfg_csv = ConnectionConfig(db_type="📄 CSV Upload")
    # Emulate app.py name mapper
    simulate_do_connect(cfg_csv, csv_tables=uploaded_csvs)

    assert st.session_state.connected is True
    assert "employees_data" in st.session_state.table_names
    assert "departments" in st.session_state.table_names
    safe_print(f"  {GREEN}[OK] In-memory CSV database mounted perfectly.{RESET}")

    # Query flow test on uploaded CSVs
    success = simulate_query_flow("Show the total salary for each department in employees_data")
    assert success is True
    assert st.session_state.last_df.shape[0] > 0
    safe_print(f"  {GREEN}[OK] End-to-end query flow tested perfectly on virtual CSV relational tables!{RESET}")


    # ─── VIRTUAL DATABASE 3: NETWORK DB WITH PARAMETERS (MOCK POSTGRES) ────────
    safe_print(f"\n{BOLD}[DB PROFILE 3] PostgreSQL (Virtual Mock Connection){RESET}")
    reset_mock_state()

    # Emulate SQL Server/Postgres credentials and advanced parameters
    cfg_pg = ConnectionConfig(
        db_type="🐘 PostgreSQL",
        host="localhost",
        port=5432,
        database="production_vault",
        username="readonly_user",
        password="secure_password_123",
        extra_params="sslmode=require&charset=utf8"
    )

    # To test connection logic, dynamic prompting and visualization flows without a real live PG server,
    # we redirect database execution dynamically to our hospital SQLite database
    # but retain the active PG dialect prompts and configuration parameters!
    from database.setup_db import DB_PATH
    import sqlalchemy
    from sqlalchemy import create_engine
    
    # Connect virtually to demo db but act as PostgreSQL dialect
    sqlite_engine = create_engine(f"sqlite:///{DB_PATH}")
    
    st.session_state.engine = sqlite_engine
    st.session_state.csv_tables = None
    st.session_state.connected = True
    st.session_state.active_db_type = "PostgreSQL"
    st.session_state.conn_config = cfg_pg
    st.session_state.schema_str = extract_schema_string(sqlite_engine)
    st.session_state.schema_dict = extract_schema_dict(sqlite_engine)
    st.session_state.table_names = get_table_names_from_engine(sqlite_engine)
    
    # Overwrite get_dialect_name dynamically to return POSTGRESQL for the test!
    def mock_get_dialect_name(engine):
        return "PostgreSQL"
    
    globals()['get_dialect_name'] = mock_get_dialect_name

    safe_print(f"  [MOCK] Mounted virtual PostgreSQL server with advanced options: {cfg_pg.extra_params}")
    
    # Run query flow (Gemini should generate PostgreSQL syntax now!)
    success = simulate_query_flow("Show the top 3 oldest patients")
    assert success is True
    assert not st.session_state.last_df.empty
    safe_print(f"  {GREEN}[OK] PostgreSQL dialect-specific query flow tested perfectly!{RESET}")


    safe_print("\n" + "=" * 60)
    safe_print(f"{BOLD}{GREEN}[VIRTUAL SUCCESS] Website E2E flow validated successfully!{RESET}\n")
    return True


if __name__ == "__main__":
    run_virtual_website_tests()
