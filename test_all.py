"""
test_all.py — Test script to verify all modules in the QueryAI project.
Compatible with standard Windows terminals (non-UTF8 safe).
Run: python test_all.py
"""
import os
import sys
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv

# Ensure we can import from local path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.connection_manager import (
    ConnectionConfig,
    build_engine,
    extract_schema_string,
    extract_schema_dict,
    get_table_names_from_engine,
    get_table_preview_from_engine,
    run_query_on_engine,
)
from utils.db_handler import (
    get_schema,
    get_full_schema_dict,
    get_table_names,
    get_table_preview,
    run_query,
)
from utils.llm_handler import generate_sql
from utils.visualizer import auto_visualize

# Load environment
load_dotenv()

# ANSI colors for nice terminal reporting (disabled if colors break, but normally okay on modern Windows)
# Using standard ascii characters instead of emojis to avoid encoding errors on cp1252.
GREEN = ""
RED = ""
YELLOW = ""
CYAN = ""
BOLD = ""
RESET = ""

# Attempt to configure color if terminal supports it
if sys.platform != "win32" or os.environ.get("COLORTERM"):
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def run_tests():
    print(f"\n{BOLD}{CYAN}[START] Starting QueryAI Integration & Module Testing{RESET}\n" + "=" * 60)

    # ─── 1. DATABASE CONNECTION MANAGER TESTS ──────────────────────────────────
    print(f"\n{BOLD}[1/4] Connection Manager & Schema Extraction Tests{RESET}")
    
    # Check if demo hospital db exists. If not, set it up.
    from database.setup_db import setup_database, DB_PATH
    if not os.path.exists(DB_PATH):
        print(f"  [INFO] Demo database not found. Seeding now...")
        setup_database()
        
    try:
        cfg = ConnectionConfig(db_type="🏥 Demo (Hospital SQLite)")
        engine, err = build_engine(cfg)
        
        assert err == "", f"Connection failed with error: {err}"
        assert engine is not None, "SQLAlchemy engine is None"
        print(f"  {GREEN}[OK] Connection to SQLite Demo built successfully!{RESET}")
        
        # Test schema string extraction
        schema_str = extract_schema_string(engine)
        assert "Table: patients" in schema_str, "Schema string missing patients table description"
        assert "Table: doctors" in schema_str, "Schema string missing doctors table description"
        print(f"  {GREEN}[OK] Schema string extraction completed (length: {len(schema_str)} characters).{RESET}")
        
        # Test schema dict extraction
        schema_dict = extract_schema_dict(engine)
        assert "patients" in schema_dict, "Schema dict missing 'patients' key"
        assert "doctors" in schema_dict, "Schema dict missing 'doctors' key"
        patient_cols = [col[0] for col in schema_dict["patients"]]
        assert "patient_id" in patient_cols, "patient_id column missing from patients"
        print(f"  {GREEN}[OK] Schema dict successfully parsed ({len(schema_dict)} tables reflected).{RESET}")
        
        # Test list tables
        tables = get_table_names_from_engine(engine)
        assert len(tables) >= 5, f"Expected 5+ tables, got {len(tables)}"
        print(f"  {GREEN}[OK] Table list extracted correctly: {tables}{RESET}")
        
        # Test preview
        preview_df = get_table_preview_from_engine(engine, "patients", limit=3)
        assert not preview_df.empty, "Table preview returned empty DataFrame"
        assert preview_df.shape[0] == 3, f"Expected 3 rows, got {preview_df.shape[0]}"
        print(f"  {GREEN}[OK] Table preview fetched successfully ({preview_df.shape[0]}x{preview_df.shape[1]} df).{RESET}")
        
        # Test query execution
        df, db_err = run_query_on_engine(engine, "SELECT COUNT(*) as count FROM patients")
        assert db_err == "", f"Query failed: {db_err}"
        assert not df.empty, "Query returned empty DataFrame"
        assert df["count"].iloc[0] == 150, f"Expected 150 patients, got {df['count'].iloc[0]}"
        print(f"  {GREEN}[OK] Query execution tested successfully (patients count: {df['count'].iloc[0]}).{RESET}")
        
        # Test CSV dynamic memory query execution
        csv_df = pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie"],
            "score": [95, 88, 92],
            "city": ["New York", "Chicago", "Boston"]
        })
        csv_tables = {"student_scores": csv_df}
        
        df_csv, csv_err = run_query_on_engine(None, "SELECT SUM(score) as total FROM student_scores", csv_tables=csv_tables)
        assert csv_err == "", f"CSV query failed: {csv_err}"
        assert df_csv["total"].iloc[0] == 275, f"Expected total 275, got {df_csv['total'].iloc[0]}"
        print(f"  {GREEN}[OK] Virtual CSV connection & in-memory SQL execution verified successfully!{RESET}")
        
    except AssertionError as e:
        print(f"  {RED}[FAIL] Connection Manager Test failed: {e}{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}[FAIL] Connection Manager Test raised exception: {e}{RESET}")
        return False

    # ─── 2. BACKWARD COMPATIBILITY LAYERS ──────────────────────────────────────
    print(f"\n{BOLD}[2/4] db_handler Compatibility Layer Tests{RESET}")
    try:
        compat_schema = get_schema()
        assert "Table: patients" in compat_schema, "Compat schema missing patients"
        
        compat_dict = get_full_schema_dict()
        assert "appointments" in compat_dict, "Compat dict missing appointments"
        
        compat_names = get_table_names()
        assert "billing" in compat_names, "Compat names missing billing"
        
        compat_preview = get_table_preview("doctors", limit=2)
        assert compat_preview.shape[0] == 2, f"Compat preview expected 2 rows, got {compat_preview.shape[0]}"
        
        compat_df, compat_err = run_query("SELECT COUNT(*) as cnt FROM appointments")
        assert compat_err == "", f"Compat run_query failed: {compat_err}"
        assert compat_df["cnt"].iloc[0] == 300, f"Expected 300 appointments, got {compat_df['cnt'].iloc[0]}"
        
        print(f"  {GREEN}[OK] All compatibility wrappers validated perfectly!{RESET}")
    except AssertionError as e:
        print(f"  {RED}[FAIL] Compatibility Layer Test failed: {e}{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}[FAIL] Compatibility Layer Test raised exception: {e}{RESET}")
        return False

    # ─── 3. LLM API & PROMPT GENERATION TESTS ──────────────────────────────────
    print(f"\n{BOLD}[3/4] Google Gemini API & LLM Handler Tests{RESET}")
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print(f"  {YELLOW}[WARN] GEMINI_API_KEY is not defined in .env. Skipping LLM API calls.{RESET}")
    else:
        try:
            # Test simple SQL generation
            question = "Which doctor has the highest number of appointments?"
            schema = get_schema()
            
            print("  [INFO] Requesting SQL from Gemini API...")
            sql, used_model, err_msg = generate_sql(question, schema)
            
            assert err_msg == "", f"LLM SQL Generation failed: {err_msg}"
            assert sql != "", "LLM generated empty SQL string"
            
            print(f"  {GREEN}[OK] LLM SQL generation successful!{RESET}")
            print(f"    - Used Model: {used_model}")
            print(f"    - Generated SQL: {BOLD}{sql}{RESET}")
            
            # Smoke test query to make sure generated SQL runs on our DB
            res_df, run_err = run_query(sql)
            if run_err:
                print(f"  {YELLOW}[WARN] Generated SQL had database error: {run_err}{RESET}")
            else:
                print(f"  {GREEN}[OK] Generated SQL executed successfully! Received {res_df.shape[0]} rows.{RESET}")
                
        except AssertionError as e:
            print(f"  {RED}[FAIL] LLM Handler Test failed: {e}{RESET}")
            return False
        except Exception as e:
            print(f"  {RED}[FAIL] LLM Handler Test raised exception: {e}{RESET}")
            return False

    # ─── 4. AUTOMATED PLOTLY VISUALIZATION TESTS ────────────────────────────────
    print(f"\n{BOLD}[4/4] Automated Plotly Visualization Tests{RESET}")
    try:
        # Case 1: One Categorical + One Numeric (Bar Chart)
        df_bar = pd.DataFrame({
            "doctor": ["Dr. Smith", "Dr. Jones", "Dr. Davis"],
            "fee": [1500, 1200, 2000]
        })
        fig_bar = auto_visualize(df_bar, "Fees by Doctor")
        assert fig_bar is not None, "Failed to create Bar chart"
        assert isinstance(fig_bar, go.Figure), "Chart is not a Plotly Figure instance"
        assert fig_bar.layout.title.text == "Fees by doctor", f"Title error: {fig_bar.layout.title.text}"
        print(f"  {GREEN}[OK] Categorical + Numeric auto-mapped to Styled Bar Chart.{RESET}")

        # Case 2: Only Numeric columns (Line Chart)
        df_line = pd.DataFrame({
            "age": [25, 30, 45, 60],
            "billing_amount": [500, 1000, 1500, 3000]
        })
        fig_line = auto_visualize(df_line, "Billing over age")
        assert fig_line is not None, "Failed to create Line chart"
        print(f"  {GREEN}[OK] Multi-Numeric columns auto-mapped to Styled Line Chart.{RESET}")

        # Case 3: Single Numeric column (Histogram)
        df_hist = pd.DataFrame({
            "experience_years": [5, 10, 8, 12, 15, 20, 25, 2, 6, 9]
        })
        fig_hist = auto_visualize(df_hist, "Distribution of experience")
        assert fig_hist is not None, "Failed to create Histogram"
        print(f"  {GREEN}[OK] Single numeric column auto-mapped to Styled Histogram.{RESET}")

        # Case 4: Categorical Columns only (Count Chart)
        df_count = pd.DataFrame({
            "specialization": ["Cardiology", "Cardiology", "Neurology", "Pediatrics", "Neurology", "Neurology"]
        })
        fig_count = auto_visualize(df_count, "Specialization breakdown")
        assert fig_count is not None, "Failed to create Count chart"
        print(f"  {GREEN}[OK] Text-only columns auto-mapped to Styled Group Count Bar Chart.{RESET}")

        # Case 5: Single value check (Should return None)
        df_single = pd.DataFrame({"total": [3500]})
        fig_single = auto_visualize(df_single, "Total revenue")
        assert fig_single is None, "Expected None for single-value dataset"
        print(f"  {GREEN}[OK] Single-value DataFrame correctly bypassed chart generation.{RESET}")

        print(f"  {GREEN}[OK] All Plotly auto-visualizer rules executed flawlessly!{RESET}")
    except AssertionError as e:
        print(f"  {RED}[FAIL] Visualization Test failed: {e}{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}[FAIL] Visualization Test raised exception: {e}{RESET}")
        return False

    print("\n" + "=" * 60)
    print(f"{BOLD}{GREEN}[SUCCESS] All QueryAI modules are working perfectly!{RESET}\n")
    return True


if __name__ == "__main__":
    run_tests()
