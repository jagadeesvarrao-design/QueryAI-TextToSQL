import os
import sys
import numpy as np
from dotenv import load_dotenv

# Ensure project directory is in sys.path and load environment
sys.path.insert(0, r"C:\Users\DELL\OneDrive\Desktop\PROJECTS\text-to-sql")
load_dotenv(r"C:\Users\DELL\OneDrive\Desktop\PROJECTS\text-to-sql\.env", override=True)

from utils.schema_pruner import (
    prune_schema, 
    _cosine_similarity, 
    _keyword_similarity,
    match_relevant_table_names,
    get_effective_schema,
)
from utils.connection_manager import (
    ConnectionConfig,
    build_engine,
    extract_table_schemas_dict,
    get_all_table_names,
    fetch_columns_for_specific_tables,
)
from utils.llm_handler import generate_sql


def test_cosine_math():
    print("Testing cosine math...")
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    
    assert abs(_cosine_similarity(v1, v2) - 1.0) < 1e-5
    assert abs(_cosine_similarity(v1, v3) - 0.0) < 1e-5
    print("✅ Cosine math passed!")


def test_3000_table_names_matching():
    print("Testing 3,000+ table names matching on-demand...")
    # Generate 3,000 simulated table names (like an enterprise SAP/Oracle ERP system)
    dummy_names = [f"tbl_module_{i}_{j}" for i in range(100) for j in range(30)]
    dummy_names.append("warehouses_archive")
    dummy_names.append("inventory_stock_logs")
    dummy_names.append("customer_billing_ledger")
    
    assert len(dummy_names) >= 3000, f"Expected 3000+ tables, got {len(dummy_names)}"
    
    # Query for warehouse archive
    q = "Show me stock levels from warehouses_archive"
    matched = match_relevant_table_names(q, dummy_names, top_k=3)
    print(f"3,000 Tables Query: '{q}' -> Matched: {matched}")
    assert "warehouses_archive" in matched, "Expected 'warehouses_archive' in matched tables!"
    print("✅ 3,000+ table name matching passed!")


def test_schema_pruning_logic():
    print("Testing schema pruning ranking...")
    # Simulate a database with 10 tables
    fake_tables = {
        "patients": "Table: patients\n Columns: patient_id, name, age, gender, city",
        "doctors": "Table: doctors\n Columns: doctor_id, name, specialization, experience_years, fee",
        "appointments": "Table: appointments\n Columns: appt_id, patient_id, doctor_id, date, status, diagnosis",
        "prescriptions": "Table: prescriptions\n Columns: pres_id, appt_id, medicine, dosage, duration_days",
        "billing": "Table: billing\n Columns: bill_id, appt_id, amount, payment_method, paid_date",
        "inventory": "Table: inventory\n Columns: item_id, item_name, quantity, warehouse_location",
        "staff_shifts": "Table: staff_shifts\n Columns: shift_id, staff_name, shift_date, department",
        "suppliers": "Table: suppliers\n Columns: supplier_id, company_name, contact_person, phone",
        "medical_devices": "Table: medical_devices\n Columns: device_id, model, serial_number, maintenance_date",
        "visitor_logs": "Table: visitor_logs\n Columns: log_id, visitor_name, patient_id, entry_time",
    }
    
    # Test query 1: Billing & Payment question
    q1 = "What is the total billing amount paid via Credit Card?"
    pruned1, selected1 = prune_schema(q1, fake_tables, top_k=3)
    print(f"Query: '{q1}' -> Selected tables: {selected1}")
    assert "billing" in selected1, "Expected 'billing' in selected tables for billing query!"
    
    # Test query 2: Doctors & appointments question
    q2 = "Which doctor has the most completed appointments?"
    pruned2, selected2 = prune_schema(q2, fake_tables, top_k=3)
    print(f"Query: '{q2}' -> Selected tables: {selected2}")
    assert "doctors" in selected2 or "appointments" in selected2, "Expected 'doctors' or 'appointments' in selected tables!"
    
    print("✅ Schema pruning ranking passed!")


def test_end_to_end_llm_with_pruning():
    print("Testing End-to-End LLM with Schema RAG...")
    cfg = ConnectionConfig(db_type="🏥 Demo (Hospital SQLite)")
    engine, err = build_engine(cfg)
    assert not err, f"Failed to build demo engine: {err}"
    
    table_schemas = extract_table_schemas_dict(engine)
    assert len(table_schemas) >= 5, f"Expected at least 5 tables, got {len(table_schemas)}"
    
    question = "Show the average billing amount for each doctor specialization"
    sql, used_model, llm_err = generate_sql(question, table_schemas, dialect="SQLite")
    assert not llm_err, f"LLM error: {llm_err}"
    assert "SELECT" in sql.upper(), f"Invalid SQL generated: {sql}"
    print(f"Generated SQL with Schema RAG:\n{sql}")
    print(f"Model used: {used_model}")
    print("✅ End-to-End LLM with Schema RAG passed!")


if __name__ == "__main__":
    test_cosine_math()
    test_3000_table_names_matching()
    test_schema_pruning_logic()
    test_end_to_end_llm_with_pruning()
    print("\n🎉 ALL SCHEMA PRUNER & 3,000+ TABLE ON-DEMAND TESTS PASSED!")
