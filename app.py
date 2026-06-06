"""
app.py — MediQuery AI | Text-to-SQL for ANY database.
Supports: MySQL, PostgreSQL, MSSQL, Oracle, SQLite, CSV Upload, Demo Hospital DB.
Run: streamlit run app.py
"""
import os
import sys
import time
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from utils.connection_manager import (
    DB_CONFIGS,
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
from database.setup_db import setup_database, DB_PATH

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QueryAI — Universal Text-to-SQL",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

/* ── Universal Reset & Typography ── */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif !important;
    background-color: #050508 !important;
    color: #E2E8F0 !important;
}
.main .block-container { 
    padding: 2rem 3rem 4rem; 
    max-width: 1350px; 
}

/* Background glowing grids/dots */
.main {
    background-image: 
        radial-gradient(at 10% 20%, rgba(16, 185, 129, 0.01) 0px, transparent 50%),
        radial-gradient(at 90% 80%, rgba(5, 150, 105, 0.02) 0px, transparent 50%),
        radial-gradient(at 50% 10%, rgba(16, 185, 129, 0.01) 0px, transparent 50%) !important;
}

/* ── Hero Banner ── */
.hero {
    background: linear-gradient(135deg, rgba(9, 10, 15, 0.9) 0%, rgba(5, 5, 8, 0.95) 100%) !important;
    border: 1px solid rgba(16, 185, 129, 0.12);
    border-radius: 24px;
    padding: 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.02);
}
.hero::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(16, 185, 129, 0.05) 0%, transparent 70%);
    pointer-events: none;
}
.hero h1 { 
    font-size: 3rem; 
    font-weight: 800; 
    color: #fff; 
    margin: 0 0 0.5rem; 
    letter-spacing: -1.5px; 
    line-height: 1.1;
}
.hero h1 span { 
    background: linear-gradient(90deg, #10B981, #059669, #00F6A5); 
    -webkit-background-clip: text; 
    -webkit-text-fill-color: transparent; 
}
.hero p { 
    color: #94A3B8; 
    font-size: 1.1rem; 
    margin: 0; 
    font-weight: 400;
}
.hero .badge-row { 
    margin-top: 1.5rem; 
    display: flex; 
    gap: 0.6rem; 
    flex-wrap: wrap; 
}
.badge {
    display: inline-flex; 
    align-items: center; 
    gap: 0.4rem;
    background: rgba(10, 10, 14, 0.6); 
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 30px; 
    padding: 0.4rem 1rem;
    font-size: 0.8rem; 
    color: #94A3B8; 
    font-weight: 600;
    transition: all 0.2s ease;
}
.badge.active { 
    background: rgba(16, 185, 129, 0.08); 
    border-color: rgba(16, 185, 129, 0.25); 
    color: #10B981; 
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.08);
}

/* ── Connection & UI Panels ── */
.conn-panel {
    background: rgba(8, 8, 12, 0.55) !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
    border-radius: 20px;
    padding: 1.75rem;
    margin-bottom: 2rem;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    transition: all 0.3s ease;
}
.conn-panel.connected { 
    border: 1px solid rgba(16, 185, 129, 0.2) !important;
    box-shadow: 0 15px 40px rgba(16, 185, 129, 0.06);
}

/* Connection status display */
.status-connected {
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: rgba(16, 185, 129, 0.08); color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 10px; padding: 0.4rem 1rem; font-size: 0.85rem; font-weight: 600;
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.04);
}
.status-disconnected {
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: rgba(239, 68, 68, 0.08); color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 10px; padding: 0.4rem 1rem; font-size: 0.85rem; font-weight: 600;
}

/* ── Inputs & Selectboxes ── */
div[data-baseweb="select"] > div {
    background-color: #06060A !important;
    border: 1px solid rgba(255, 255, 255, 0.04) !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
}
.stTextInput input, .stNumberInput input {
    background-color: #06060A !important;
    color: #E2E8F0 !important;
    border: 1px solid rgba(255, 255, 255, 0.04) !important;
    border-radius: 10px !important;
    padding: 0.55rem 0.75rem !important;
    font-size: 0.9rem !important;
    transition: all 0.2s ease !important;
}
.stTextInput input:focus, .stNumberInput input:focus, div[data-baseweb="select"]:focus-within {
    border-color: #10B981 !important;
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.12) !important;
}
.stTextArea textarea {
    background-color: #040508 !important;
    color: #ECFDF5 !important;
    border: 1px solid rgba(255, 255, 255, 0.04) !important;
    border-radius: 16px !important;
    font-size: 1.05rem !important;
    padding: 1.2rem !important;
    transition: all 0.2s ease !important;
    line-height: 1.5 !important;
}
.stTextArea textarea:focus {
    border-color: #10B981 !important;
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.15) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
    color: #050508 !important; 
    border: none !important;
    border-radius: 12px !important; 
    font-weight: 700 !important;
    padding: 0.7rem 1.8rem !important; 
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.2) !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    font-size: 0.85rem !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(16, 185, 129, 0.35) !important;
    color: #050508 !important;
}
.stButton > button:active {
    transform: translateY(0px) !important;
}

/* Disconnect button styling (override gradient) */
div.element-container:has(button[key="disconnect_btn"]) button,
button[key*="disconnect"] {
    background: rgba(239, 68, 68, 0.08) !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
    color: #F87171 !important;
    box-shadow: none !important;
    text-transform: none !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}
div.element-container:has(button[key="disconnect_btn"]) button:hover,
button[key*="disconnect"]:hover {
    background: rgba(239, 68, 68, 0.15) !important;
    border-color: #F87171 !important;
    color: #fff !important;
}

/* ── Section labels ── */
.section-label {
    font-size: 0.72rem; 
    font-weight: 800; 
    color: #4B5563;
    text-transform: uppercase; 
    letter-spacing: 2px; 
    margin-bottom: 0.75rem;
    margin-top: 0.5rem;
}

/* ── Sidebar Styling ── */
[data-testid="stSidebar"] {
    background-color: #030305 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.02) !important;
}

/* Sidebar navigation radios */
div[data-testid="stSidebar"] div.stRadio > label {
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #475569;
}
div[data-testid="stSidebar"] div.stRadio div[role="radiogroup"] {
    gap: 8px;
}
div[data-testid="stSidebar"] div.stRadio div[role="radiogroup"] label {
    background: rgba(255, 255, 255, 0.01) !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
    padding: 0.6rem 0.8rem !important;
    border-radius: 10px !important;
    transition: all 0.2s ease;
    cursor: pointer;
}
div[data-testid="stSidebar"] div.stRadio div[role="radiogroup"] label:hover {
    background: rgba(16, 185, 129, 0.02) !important;
    border-color: rgba(16, 185, 129, 0.15) !important;
}
div[data-testid="stSidebar"] div.stRadio div[role="radiogroup"] div[data-checked="true"] label {
    background: rgba(16, 185, 129, 0.06) !important;
    border-color: #10B981 !important;
    color: #10B981 !important;
}

/* ── Expander Panels ── */
.streamlit-expanderHeader {
    background-color: #06060A !important;
    border: 1px solid rgba(255, 255, 255, 0.03) !important;
    border-radius: 12px !important;
    color: #E2E8F0 !important;
    font-weight: 600 !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.9rem !important;
    transition: all 0.2s ease !important;
}
.streamlit-expanderHeader:hover {
    border-color: rgba(16, 185, 129, 0.20) !important;
    color: #10B981 !important;
}
.streamlit-expanderContent {
    background-color: rgba(6, 6, 10, 0.4) !important;
    border-left: 1px solid rgba(255, 255, 255, 0.02) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.02) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.02) !important;
    border-radius: 0 0 12px 12px !important;
    padding: 1.25rem !important;
}

/* ── Metric Cards ── */
.metric-row { 
    display: flex; 
    gap: 1.25rem; 
    margin: 1.5rem 0; 
    flex-wrap: wrap; 
}
.metric-card {
    flex: 1; 
    min-width: 120px;
    background: rgba(8, 8, 12, 0.6) !important; 
    border: 1px solid rgba(16, 185, 129, 0.12) !important;
    border-radius: 16px; 
    padding: 1.25rem 1rem; 
    text-align: center;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
    transition: all 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(16, 185, 129, 0.3) !important;
    box-shadow: 0 12px 30px rgba(16, 185, 129, 0.08);
}
.metric-card .mv { 
    font-size: 2.2rem; 
    font-weight: 800; 
    color: #10B981; 
    background: linear-gradient(90deg, #10B981, #00F6A5);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
}
.metric-card .ml { 
    font-size: 0.78rem; 
    color: #64748B; 
    margin-top: 0.5rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ── SQL View Cards ── */
.sql-card {
    background: #030406 !important; 
    border: 1px solid rgba(16, 185, 129, 0.15) !important;
    border-left: 4px solid #10B981 !important;
    border-radius: 12px; 
    padding: 1.5rem; 
    margin-bottom: 1.25rem;
    box-shadow: inset 0 2px 10px rgba(0,0,0,0.9);
}
.sql-card pre {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.95rem !important;
    color: #00F6A5 !important;
    margin: 0;
}

/* ── Tabs Restyling ── */
.stTabs [data-baseweb="tab-list"] { 
    background: #06060A !important; 
    border-radius: 14px; 
    padding: 6px; 
    gap: 6px; 
    border: 1px solid rgba(255,255,255,0.02) !important;
}
.stTabs [data-baseweb="tab"] { 
    background: transparent !important; 
    color: #64748B !important; 
    border-radius: 10px !important; 
    font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.2s ease !important;
    border: none !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #E2E8F0 !important;
}
.stTabs [aria-selected="true"] { 
    background: rgba(16, 185, 129, 0.06) !important; 
    color: #10B981 !important; 
    border: 1px solid rgba(16, 185, 129, 0.15) !important;
}

/* ── History Panel ── */
.hist-item {
    background: rgba(10, 10, 14, 0.3); 
    border: 1px solid rgba(255,255,255,0.01);
    border-left: 3px solid #10B981;
    border-radius: 0 10px 10px 0; 
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.5rem; 
    font-size: 0.82rem; 
    color: #94A3B8;
    transition: all 0.2s ease;
}
.hist-item:hover {
    background: rgba(16, 185, 129, 0.03);
    border-color: rgba(16, 185, 129, 0.08);
    border-left-color: #00F6A5;
    color: #E2E8F0;
}

/* ── File Uploader ── */
[data-testid="stFileUploader"] { 
    background: rgba(8, 8, 12, 0.5); 
    border: 2px dashed rgba(16, 185, 129, 0.15); 
    border-radius: 16px; 
    padding: 1.5rem; 
    transition: all 0.2s ease;
}
[data-testid="stFileUploader"]:hover {
    border-color: #10B981;
    background: rgba(16, 185, 129, 0.01);
}

/* ── Errors and Info ── */
.error-box {
    background: rgba(239, 68, 68, 0.06) !important; 
    border: 1px solid rgba(239, 68, 68, 0.25) !important;
    border-left: 4px solid #EF4444 !important;
    border-radius: 12px; 
    padding: 1.25rem; 
    color: #FCA5A5;
    font-size: 0.92rem;
    line-height: 1.5;
}

/* Hide default streamlit indicators */
#MainMenu, footer, header { visibility: hidden; }

/* ── Custom Scrollbar ── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #050508; }
::-webkit-scrollbar-thumb { background: #111827; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #1F2937; }
</style>
""", unsafe_allow_html=True)

# ─── Session State ─────────────────────────────────────────────────────────────
defaults = {
    "engine": None,
    "csv_tables": None,
    "connected": False,
    "active_db_type": "🏥 Demo (Hospital SQLite)",
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
    "app_mode": "🔍 Query Console",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Auto-init Demo DB on first load ──────────────────────────────────────────
if not st.session_state.connected and not os.path.exists(DB_PATH):
    with st.spinner("🔧 Creating demo hospital database..."):
        setup_database()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def do_connect(config: ConnectionConfig, csv_tables=None):
    """Attempt connection and update session state."""
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
        st.success(f"✅ Loaded {len(csv_tables)} CSV table(s)!")
        return

    engine, err = build_engine(config)
    if err:
        st.error(f"❌ Connection failed: {err}")
        return

    st.session_state.engine = engine
    st.session_state.csv_tables = None
    st.session_state.connected = True
    st.session_state.active_db_type = config.db_type
    st.session_state.conn_config = config
    st.session_state.schema_str = extract_schema_string(engine)
    st.session_state.schema_dict = extract_schema_dict(engine)
    st.session_state.table_names = get_table_names_from_engine(engine)
    # Clear previous results when switching DB
    st.session_state.last_df = None
    st.session_state.last_sql = ""
    st.session_state.last_question = ""
    st.success(f"✅ Connected to {config.db_type}! Found {len(st.session_state.table_names)} tables.")

# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Logo
    st.markdown("""
    <div style="padding: 1rem 0 0.5rem; text-align:center;">
        <div style="font-size:2rem;">🧠</div>
        <div style="font-size:1rem; font-weight:700; color:#10B981;">QueryAI</div>
        <div style="font-size:0.7rem; color:#475569;">Universal Text-to-SQL</div>
    </div>
    <hr style="border-color:#1E293B; margin:0.5rem 0 1rem;">
    """, unsafe_allow_html=True)

    # ── Navigation ──
    st.markdown('<div class="section-label">🧭 Navigation</div>', unsafe_allow_html=True)
    app_mode = st.radio(
        "Navigation",
        options=["🔍 Query Console", "📖 Database Setup Guide"],
        index=0,
        key="app_mode",
        label_visibility="collapsed"
    )
    st.markdown('<hr style="border-color:#1E293B; margin:0.5rem 0 1rem;">', unsafe_allow_html=True)

    # ── Connection Status ──
    if st.session_state.connected:
        db_icon = DB_CONFIGS.get(st.session_state.active_db_type, {}).get("icon", "🗄️")
        st.markdown(
            f'<div class="status-connected">🟢 {db_icon} {st.session_state.active_db_type.split(" ", 1)[-1]}</div>',
            unsafe_allow_html=True
        )
        if st.button("🔌 Disconnect", width="stretch", key="disconnect_btn"):
            for k in ["engine", "csv_tables", "connected", "schema_str",
                      "schema_dict", "table_names", "last_df", "last_sql"]:
                st.session_state[k] = defaults[k]
            st.rerun()
    else:
        st.markdown('<div class="status-disconnected">🔴 Not Connected</div>', unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1E293B; margin:0.75rem 0;">', unsafe_allow_html=True)

    # ── Model Selection ──
    st.markdown('<div class="section-label">🤖 AI Model Settings</div>', unsafe_allow_html=True)
    selected_model = st.selectbox(
        "Select Gemini Model",
        options=[
            "gemini-2.5-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.5-pro",
        ],
        index=0,
        key="selected_model",
        label_visibility="collapsed"
    )
    st.markdown('<hr style="border-color:#1E293B; margin:0.75rem 0;">', unsafe_allow_html=True)

    # ── Schema Viewer ──
    if st.session_state.connected and st.session_state.schema_dict:
        st.markdown('<div class="section-label">📋 Schema</div>', unsafe_allow_html=True)
        for tname, cols in st.session_state.schema_dict.items():
            with st.expander(f"🗂️ {tname} ({len(cols)} cols)"):
                for cname, ctype in cols:
                    icon = "🔑" if cname.lower().endswith("_id") or cname.lower() == "id" else "📌"
                    st.markdown(
                        f'<div style="font-size:0.78rem;color:#94A3B8;padding:2px 0">'
                        f'{icon} <b style="color:#CBD5E1">{cname}</b> '
                        f'<span style="color:#475569">({ctype})</span></div>',
                        unsafe_allow_html=True
                    )

        # Table Preview
        st.markdown('<hr style="border-color:#1E293B;margin:0.75rem 0">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">👁️ Table Preview</div>', unsafe_allow_html=True)
        if st.session_state.table_names:
            sel_tbl = st.selectbox("Table", st.session_state.table_names, label_visibility="collapsed")
            prev_df = get_table_preview_from_engine(
                st.session_state.engine, sel_tbl, 4,
                csv_tables=st.session_state.csv_tables
            )
            st.dataframe(prev_df, width="stretch", hide_index=True)

    # ── Query History ──
    if st.session_state.query_history:
        st.markdown('<hr style="border-color:#1E293B;margin:0.75rem 0">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">🕐 History</div>', unsafe_allow_html=True)
        for i, q in enumerate(reversed(st.session_state.query_history[-6:])):
            short = q[:55] + "..." if len(q) > 55 else q
            st.markdown(f'<div class="hist-item">{i+1}. {short}</div>', unsafe_allow_html=True)

    # Footer
    model_name_display = st.session_state.get('last_used_model') or st.session_state.get('selected_model') or 'Gemini API'
    st.markdown(f"""
    <hr style="border-color:#1E293B;margin:0.75rem 0">
    <div style="text-align:center;font-size:0.68rem;color:#334155;">
        Powered by Google {model_name_display}<br>
        SQLAlchemy · Streamlit · Plotly
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

# ── Hero ──────────────────────────────────────────────────────────────────────
connected_badge = (
    f'<span class="badge active">🟢 {st.session_state.active_db_type}</span>'
    if st.session_state.connected
    else '<span class="badge">🔴 Not Connected</span>'
)

model_badge = st.session_state.get('last_used_model') or st.session_state.get('selected_model') or 'Gemini API'
st.markdown(f"""
<div class="hero">
    <h1>🧠 <span>QueryAI</span></h1>
    <p>Ask questions in plain English against ANY database — MySQL, PostgreSQL, MSSQL, Oracle, SQLite, or CSV</p>
    <div class="badge-row">
        {connected_badge}
        <span class="badge">🤖 {model_badge}</span>
        <span class="badge">⚡ Real-time SQL</span>
        <span class="badge">📊 Auto Charts</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Navigation Routing ────────────────────────────────────────────────────────
if st.session_state.get("app_mode") == "📖 Database Setup Guide":
    st.markdown("""
    <style>
    .guide-card {
        background: #06060A;
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        padding: 2rem;
        margin-top: 1.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.35);
    }
    .guide-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.25rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.02);
        padding-bottom: 0.75rem;
    }
    .guide-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #10B981;
        margin: 0;
    }
    .guide-steps {
        font-size: 0.95rem;
        color: #94A3B8;
        line-height: 1.6;
    }
    .guide-steps b {
        color: #E2E8F0;
    }
    .code-block {
        background: #040508;
        border: 1px solid rgba(16, 185, 129, 0.15);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.88rem;
        color: #00F6A5;
        margin: 0.75rem 0;
        overflow-x: auto;
    }
    .guide-steps ul {
        margin-top: 0.5rem;
        margin-bottom: 0.75rem;
        padding-left: 1.25rem;
    }
    .guide-steps li {
        margin-bottom: 0.35rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📖 Database Integration & Setup Guide")
    st.markdown("QueryAI allows you to run English queries on your own external database servers or CSV files. Choose your database type to view connection requirements.")

    t_mysql, t_pg, t_mssql, t_oracle, t_sqlite, t_csv = st.tabs([
        "🐬 MySQL", "🐘 PostgreSQL", "🪟 SQL Server", "🔴 Oracle", "📁 SQLite", "📄 CSV File"
    ])

    with t_mysql:
        st.markdown("""
        <div class="guide-card">
            <div class="guide-header">
                <span style="font-size:1.8rem;">🐬</span>
                <h4 class="guide-title">MySQL Connection Guide</h4>
            </div>
            <div class="guide-steps">
                <b>Step 1 — Install Required Packages</b><br>
                Open your local command line and install the PyMySQL connector:
                <div class="code-block">pip install pymysql</div>
                <br>
                <b>Step 2 — Fill Connection Parameters</b><br>
                Go to the <b>Query Console</b>, select <b>🐬 MySQL</b> from the database selector, and enter:
                <ul>
                    <li><b>Host / Server IP:</b> Hostname (e.g. <code>localhost</code>, <code>127.0.0.1</code>, or a remote server IP)</li>
                    <li><b>Port:</b> <code>3306</code> (default MySQL port)</li>
                    <li><b>Database Name:</b> Target database name to execute queries against</li>
                    <li><b>Username & Password:</b> Database user credentials with read permissions</li>
                </ul>
                <b>Step 3 — Run & Connect</b><br>
                Click <b>🧪 Test Connection</b> first to verify connectivity. Then click <b>🚀 Connect & Load Schema</b> to activate the console!
            </div>
        </div>
        """, unsafe_allow_html=True)

    with t_pg:
        st.markdown("""
        <div class="guide-card">
            <div class="guide-header">
                <span style="font-size:1.8rem;">🐘</span>
                <h4 class="guide-title">PostgreSQL Connection Guide</h4>
            </div>
            <div class="guide-steps">
                <b>Step 1 — Install Required Packages</b><br>
                Open your local command line and install the Psycopg2 connector:
                <div class="code-block">pip install psycopg2-binary</div>
                <br>
                <b>Step 2 — Fill Connection Parameters</b><br>
                Go to the <b>Query Console</b>, select <b>🐘 PostgreSQL</b>, and enter:
                <ul>
                    <li><b>Host / Server IP:</b> Server hostname or IP address</li>
                    <li><b>Port:</b> <code>5432</code> (default PostgreSQL port)</li>
                    <li><b>Database Name:</b> Target database name</li>
                    <li><b>Username & Password:</b> DB account username and password</li>
                </ul>
                <b>Step 3 — Connect</b><br>
                Use <b>🧪 Test Connection</b> to verify. Once confirmed, hit <b>🚀 Connect & Load Schema</b>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with t_mssql:
        st.markdown("""
        <div class="guide-card">
            <div class="guide-header">
                <span style="font-size:1.8rem;">🪟</span>
                <h4 class="guide-title">Microsoft SQL Server (MSSQL) Connection Guide</h4>
            </div>
            <div class="guide-steps">
                <b>Step 1 — Install Required Packages</b><br>
                Open your local command line and install the PyMSSQL connector:
                <div class="code-block">pip install pymssql</div>
                <br>
                <b>Step 2 — Fill Connection Parameters</b><br>
                Go to the <b>Query Console</b>, select <b>🪟 Microsoft SQL Server</b>, and enter:
                <ul>
                    <li><b>Host / Server IP:</b> Server IP or Hostname (include instance name if applicable, e.g. <code>MYSERVER\\SQLEXPRESS</code>)</li>
                    <li><b>Port:</b> <code>1433</code> (default MSSQL port)</li>
                    <li><b>Database Name:</b> Target database name</li>
                    <li><b>Username & Password:</b> SQL Server login credentials</li>
                </ul>
                <b>Step 3 — Advanced Configuration</b><br>
                If using local or self-signed SQL Server certificates, open the <b>Advanced Options</b> expander and type:
                <div class="code-block">TrustServerCertificate=yes</div>
                <br>
                <b>Step 4 — Test & Connect</b><br>
                Click <b>🧪 Test Connection</b>, then click <b>🚀 Connect & Load Schema</b>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with t_oracle:
        st.markdown("""
        <div class="guide-card">
            <div class="guide-header">
                <span style="font-size:1.8rem;">🔴</span>
                <h4 class="guide-title">Oracle SQL Connection Guide</h4>
            </div>
            <div class="guide-steps">
                <b>Step 1 — Install Required Packages</b><br>
                Open your local command line and install the Oracle thin driver package:
                <div class="code-block">pip install oracledb</div>
                <br>
                <b>Step 2 — Fill Connection Parameters</b><br>
                Go to the <b>Query Console</b>, select <b>🔴 Oracle SQL</b>, and enter:
                <ul>
                    <li><b>Host / Server IP:</b> Server hostname or IP address</li>
                    <li><b>Port:</b> <code>1521</code> (default Oracle port)</li>
                    <li><b>Database Name:</b> Service Name or SID (e.g. <code>XE</code>, <code>ORCL</code>)</li>
                    <li><b>Username & Password:</b> Oracle user credentials</li>
                </ul>
                <b>Step 3 — Connect</b><br>
                Click <b>🧪 Test Connection</b>, then click <b>🚀 Connect & Load Schema</b>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with t_sqlite:
        st.markdown("""
        <div class="guide-card">
            <div class="guide-header">
                <span style="font-size:1.8rem;">📁</span>
                <h4 class="guide-title">SQLite Connection Guide</h4>
            </div>
            <div class="guide-steps">
                <b>Step 1 — No Drivers Required</b><br>
                SQLite support is built natively into Python. No packages need to be installed.
                <br><br>
                <b>Step 2 — Fill Connection Parameters</b><br>
                Go to the <b>Query Console</b>, select <b>📁 SQLite (File)</b>, and enter:
                <ul>
                    <li><b>SQLite File Path:</b> The absolute system path to your database file.</li>
                    <li><b>Example Windows Path:</b> <code>C:/Users/DELL/projects/text-to-sql/database/hospital.db</code></li>
                    <li><b>Example Mac/Linux Path:</b> <code>/Users/name/projects/text-to-sql/database/hospital.db</code></li>
                </ul>
                <b>Step 3 — Connect</b><br>
                Click <b>Connect to SQLite File</b> to extract the schema and load the query interface.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with t_csv:
        st.markdown("""
        <div class="guide-card">
            <div class="guide-header">
                <span style="font-size:1.8rem;">📄</span>
                <h4 class="guide-title">CSV File Connection Guide</h4>
            </div>
            <div class="guide-steps">
                <b>Step 1 — Upload Your CSVs</b><br>
                Go to the <b>Query Console</b>, select <b>📄 CSV Upload</b>, and drag & drop one or multiple CSV files.
                <br><br>
                <b>Step 2 — Automatic Schema Creation</b><br>
                QueryAI reads your CSV column headers and converts them to virtual SQL tables.
                <ul>
                    <li>The table name matches the file name (e.g., <code>employees_data.csv</code> will become the table <code>employees_data</code>).</li>
                </ul>
                <b>Step 3 — Click Load Data</b><br>
                Click <b>📊 Load CSV Data</b>. You can now query your files in plain English:
                <div class="code-block">Show the total salary by department in employees_data</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE CONNECTION PANEL
# ═══════════════════════════════════════════════════════════════════════════════
panel_class = "conn-panel connected" if st.session_state.connected else "conn-panel"

st.markdown(f'<div class="{panel_class}">', unsafe_allow_html=True)

with st.expander(
    "🔌 **Database Connection** — Connect to MySQL, PostgreSQL, MSSQL, Oracle, SQLite, or CSV",
    expanded=True
):
    # ── DB Type Selector ──
    db_types = list(DB_CONFIGS.keys())
    selected_idx = db_types.index(st.session_state.active_db_type) if st.session_state.active_db_type in db_types else 0
    selected_db = st.selectbox(
        "Select Database Type",
        db_types,
        index=selected_idx,
        key="db_type_selector"
    )
    db_info = DB_CONFIGS[selected_db]

    # Reset default port when database type changes (resolves Streamlit's state persistence bug)
    if "last_selected_db" not in st.session_state:
        st.session_state.last_selected_db = selected_db
    if st.session_state.last_selected_db != selected_db:
        new_default_port = db_info.get("default_port")
        if new_default_port is not None:
            st.session_state["db_port"] = new_default_port
        st.session_state.last_selected_db = selected_db

    # Show description
    st.markdown(
        f'<div style="font-size:0.82rem;color:#64748B;margin-bottom:1rem;">'
        f'{db_info["icon"]} {db_info["description"]}</div>',
        unsafe_allow_html=True
    )

    # ── Form based on selected DB type ──────────────────────────────────────
    if selected_db == "🏥 Demo (Hospital SQLite)":
        st.markdown("""
        <div style="background:rgba(16, 185, 129, 0.06);border:1px solid rgba(16, 185, 129, 0.20);
                    border-radius:10px;padding:1rem;font-size:0.9rem;color:#94A3B8;">
            🎉 <b style="color:#10B981">Ready to use!</b> The hospital demo database includes:<br>
            👥 150 patients &nbsp;|&nbsp; 👨‍⚕️ 20 doctors &nbsp;|&nbsp;
            📅 300 appointments &nbsp;|&nbsp; 💊 prescriptions &nbsp;|&nbsp; 💳 billing records
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Load Demo Database", key="load_demo", width="stretch"):
            if not os.path.exists(DB_PATH):
                setup_database()
            cfg = ConnectionConfig(db_type="🏥 Demo (Hospital SQLite)")
            do_connect(cfg)
            st.rerun()

    elif selected_db == "📄 CSV Upload":
        st.markdown('<div class="section-label">Upload CSV Files (you can upload multiple)</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Upload CSV files",
            type=["csv"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="csv_uploader"
        )
        if uploaded_files:
            st.markdown(f'**{len(uploaded_files)} file(s) selected:**')
            csv_preview = {}
            for uf in uploaded_files:
                table_name = os.path.splitext(uf.name)[0].replace(" ", "_").replace("-", "_").lower()
                df = pd.read_csv(uf)
                csv_preview[table_name] = df
                st.markdown(
                    f'<div style="font-size:0.82rem;color:#94A3B8;padding:3px 0;">'
                    f'📄 <b>{uf.name}</b> → table: <code>{table_name}</code> '
                    f'({len(df)} rows × {len(df.columns)} cols)</div>',
                    unsafe_allow_html=True
                )
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📊 Load CSV Data", key="load_csv", width="stretch"):
                cfg = ConnectionConfig(db_type="📄 CSV Upload")
                do_connect(cfg, csv_tables=csv_preview)
                st.rerun()

    elif selected_db == "📁 SQLite (File)":
        sqlite_path = st.text_input(
            "SQLite File Path",
            placeholder="C:/path/to/your/database.db",
            key="sqlite_path_input"
        )
        if st.button("🔌 Connect to SQLite File", key="connect_sqlite", width="stretch"):
            cfg = ConnectionConfig(db_type="📁 SQLite (File)", sqlite_path=sqlite_path)
            do_connect(cfg)
            if st.session_state.connected:
                st.rerun()

    else:
        # Network databases: MySQL, PostgreSQL, MSSQL, Oracle
        default_port = db_info.get("default_port", 3306)

        col1, col2 = st.columns([3, 1])
        with col1:
            host = st.text_input("Host / Server IP", placeholder="localhost or 192.168.1.1", key="db_host")
        with col2:
            port = st.number_input("Port", value=default_port, step=1, key="db_port")

        database = st.text_input("Database Name", placeholder="my_database", key="db_name")

        col3, col4 = st.columns(2)
        with col3:
            username = st.text_input("Username", placeholder="root", key="db_user")
        with col4:
            password = st.text_input("Password", type="password", placeholder="••••••••", key="db_pass")

        # Optional: extra connection params
        with st.expander("⚙️ Advanced Options"):
            extra = st.text_input(
                "Extra connection params",
                placeholder="e.g. TrustServerCertificate=yes (for MSSQL)",
                key="db_extra"
            )
            st.markdown(
                '<div style="font-size:0.75rem;color:#475569;">Leave blank for default settings.</div>',
                unsafe_allow_html=True
            )

        # Connector install hint
        connector_hints = {
            "🐬 MySQL": "💡 Requires: `pip install pymysql`",
            "🐘 PostgreSQL": "💡 Requires: `pip install psycopg2-binary`",
            "🪟 Microsoft SQL Server": "💡 Requires: `pip install pymssql`",
            "🔴 Oracle SQL": "💡 Requires: `pip install oracledb`",
        }
        if selected_db in connector_hints:
            st.markdown(
                f'<div style="font-size:0.78rem;color:#64748B;margin-top:0.5rem;">'
                f'{connector_hints[selected_db]}</div>',
                unsafe_allow_html=True
            )

        col_test, col_connect = st.columns(2)
        with col_test:
            if st.button("🧪 Test Connection", key="test_conn", width="stretch"):
                with st.spinner("Testing..."):
                    cfg = ConnectionConfig(
                        db_type=selected_db, host=host, port=int(port),
                        database=database, username=username, password=password
                    )
                    engine, err = build_engine(cfg)
                if err:
                    st.error(f"❌ {err}")
                else:
                    dialect = get_dialect_name(engine)
                    st.success(f"✅ Connection successful! Dialect: {dialect}")
                    engine.dispose()

        with col_connect:
            if st.button("🚀 Connect & Load Schema", key="connect_db", width="stretch"):
                with st.spinner(f"Connecting to {selected_db}..."):
                    cfg = ConnectionConfig(
                        db_type=selected_db, host=host, port=int(port),
                        database=database, username=username, password=password
                    )
                    do_connect(cfg)
                if st.session_state.connected:
                    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ─── Guard: must be connected to query ────────────────────────────────────────
if not st.session_state.connected:
    st.markdown("""
    <div style="text-align:center;padding:5rem 2rem;color:#475569;">
        <div style="font-size:3rem;margin-bottom:1rem;">🔌</div>
        <div style="font-size:1.2rem;font-weight:600;color:#64748B;margin-bottom:0.5rem;">
            Connect a database to get started
        </div>
        <div style="font-size:0.9rem;">
            Choose a database type above and click Connect.<br>
            New here? Try the <b style="color:#00C9A7">🏥 Demo Hospital Database</b> — no setup needed!
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
#  QUERY SECTION (only shown when connected)
# ═══════════════════════════════════════════════════════════════════════════════

# ── Dynamic Sample Questions ──────────────────────────────────────────────────
SAMPLE_QUESTIONS_MAP = {
    "🏥 Demo (Hospital SQLite)": [
        "Which doctor has the most appointments?",
        "Show total revenue by payment method",
        "List all patients diagnosed with Diabetes Type 2",
        "Average billing amount per specialization",
        "How many male vs female patients?",
        "Top 5 most prescribed medicines",
        "Which city has the most patients?",
        "Doctors with more than 15 appointments",
        "Patients older than 60 from Mumbai",
        "Total billing amount for completed appointments",
    ],
    "📄 CSV Upload": [
        "Show first 10 rows",
        "How many rows are in this table?",
        "Show all column names",
        "What is the average of numeric columns?",
        "Show distinct values in the first column",
    ],
}
DEFAULT_SAMPLES = [
    "Show all records", "How many rows are there?",
    "Show distinct values in the first column",
    "What is the maximum value?", "Count rows grouped by category",
]
sample_qs = SAMPLE_QUESTIONS_MAP.get(st.session_state.active_db_type, DEFAULT_SAMPLES)

# Table info for context
n_tables = len(st.session_state.table_names)
db_icon = DB_CONFIGS.get(st.session_state.active_db_type, {}).get("icon", "🗄️")

st.markdown(f"""
<div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">
    <div style="font-size:0.85rem;color:#475569;">
        {db_icon} <b style="color:#94A3B8">{st.session_state.active_db_type}</b>
        &nbsp;·&nbsp; {n_tables} table(s) loaded
        &nbsp;·&nbsp; <span style="color:#00C9A7">●</span> Ready to query
    </div>
</div>
""", unsafe_allow_html=True)

# ── Sample Questions ───────────────────────────────────────────────────────────
st.markdown('<div class="section-label">💡 Sample Questions</div>', unsafe_allow_html=True)
q_cols = st.columns(5)
for idx, q in enumerate(sample_qs[:10]):
    with q_cols[idx % 5]:
        if st.button(q, key=f"sq_{idx}", width="stretch"):
            st.session_state.current_question = q

st.markdown("<br>", unsafe_allow_html=True)

# ── Query Input ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">🔍 Ask Your Question</div>', unsafe_allow_html=True)
col_q, col_btn = st.columns([5, 1])
with col_q:
    user_question = st.text_area(
        "Question",
        value=st.session_state.current_question,
        placeholder="e.g. Which department has the highest average salary?",
        height=85,
        label_visibility="collapsed",
        key="question_input",
    )
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("⚡ Run", width="stretch", key="run_query_btn")

# ── Execute ────────────────────────────────────────────────────────────────────
if run_btn and user_question.strip():
    question = user_question.strip()
    with st.spinner("🤖 Gemini is generating SQL..."):
        t0 = time.time()
        # Dynamically determine the active database SQL dialect
        if st.session_state.active_db_type == "📄 CSV Upload":
            active_dialect = "SQLite"
        elif st.session_state.engine:
            active_dialect = get_dialect_name(st.session_state.engine)
        else:
            active_dialect = "SQLite"

        sql, used_model, llm_err = generate_sql(
            question, 
            st.session_state.schema_str, 
            dialect=active_dialect,
            model_name=st.session_state.get("selected_model")
        )
        gen_time = round(time.time() - t0, 2)

    if llm_err:
        st.session_state.last_used_model = ""
        st.markdown(
            f'<div class="error-box">❌ <b>AI Error:</b> {llm_err}<br><br>'
            f'💡 <i>Tip: If you hit a quota error (429), try switching the Gemini Model in the sidebar!</i></div>',
            unsafe_allow_html=True
        )
    else:
        st.session_state.last_used_model = used_model
        df, db_err = run_query_on_engine(
            st.session_state.engine, sql,
            csv_tables=st.session_state.csv_tables
        )
        st.session_state.last_sql = sql
        st.session_state.last_df = df
        st.session_state.last_question = question
        st.session_state.gen_time = gen_time
        if question not in st.session_state.query_history:
            st.session_state.query_history.append(question)

        if db_err:
            st.markdown(
                f'<div class="error-box">❌ <b>SQL Error:</b> {db_err}<br><br>'
                f'<b>Generated SQL was:</b><br><code style="color:#F87171">{sql}</code></div>',
                unsafe_allow_html=True
            )

# ── Results ────────────────────────────────────────────────────────────────────
if st.session_state.last_df is not None and not st.session_state.last_df.empty:
    df = st.session_state.last_df
    sql = st.session_state.last_sql
    question = st.session_state.last_question
    rows, cols_n = df.shape

    # Metrics
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card"><div class="mv">{rows}</div><div class="ml">Rows</div></div>
        <div class="metric-card"><div class="mv">{cols_n}</div><div class="ml">Columns</div></div>
        <div class="metric-card"><div class="mv">{st.session_state.gen_time}s</div><div class="ml">AI Time</div></div>
        <div class="metric-card"><div class="mv">✓</div><div class="ml">Success</div></div>
    </div>
    """, unsafe_allow_html=True)

    tab_data, tab_chart, tab_sql = st.tabs(["📊 Data Table", "📈 Auto Chart", "🧠 Generated SQL"])

    with tab_data:
        st.dataframe(df, width="stretch", hide_index=True, height=min(420, 45 + rows * 38))
        csv_export = df.to_csv(index=False)
        st.download_button("⬇️ Download CSV", csv_export, "results.csv", "text/csv")

    with tab_chart:
        fig = auto_visualize(df, question)
        if fig:
            st.plotly_chart(fig, width="stretch")
        else:
            st.markdown("""
            <div style="text-align:center;padding:3rem;color:#475569;">
                <div style="font-size:2rem;">📊</div>
                Chart not available for this result.<br>
                Try a query with GROUP BY + COUNT/SUM/AVG.
            </div>""", unsafe_allow_html=True)

    with tab_sql:
        st.markdown('<div class="section-label">AI-Generated SQL</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="sql-card"><pre style="color:#00C9A7;margin:0;font-size:0.9rem;'
            f'white-space:pre-wrap;">{sql}</pre></div>',
            unsafe_allow_html=True
        )
        db_name = st.session_state.active_db_type
        st.markdown(
            f'<div style="font-size:0.8rem;color:#475569;">💡 This SQL was generated by Gemini for '
            f'<b style="color:#64748B">{db_name}</b> syntax and executed on your database.</div>',
            unsafe_allow_html=True
        )

elif st.session_state.last_df is not None and st.session_state.last_df.empty:
    st.info("Query ran successfully but returned 0 rows.")

else:
    # Idle state — show how it works
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#475569;">
        <div style="font-size:3rem;margin-bottom:1rem;">💬</div>
        <div style="font-size:1.1rem;font-weight:600;color:#64748B;margin-bottom:0.5rem;">
            You're connected! Ask your first question.
        </div>
        <div style="font-size:0.9rem;">
            Type any question in plain English or click a sample question above.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── How It Works ───────────────────────────────────────────────────────────────
with st.expander("ℹ️ How it works & Supported Databases"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        **1. Connect**
        
        Choose your database type: MySQL, PostgreSQL, MSSQL, Oracle, SQLite, or upload a CSV file.
        """)
    with col2:
        st.markdown("""
        **2. Ask**
        
        Type any question in plain English. No SQL knowledge needed!
        """)
    with col3:
        st.markdown("""
        **3. AI Generates SQL**
        
        Gemini reads your database schema and writes the perfect SQL query for your DB engine.
        """)
    with col4:
        st.markdown("""
        **4. See Results**
        
        Results appear as an interactive table + auto-generated chart. Download as CSV!
        """)

    st.markdown("---")
    st.markdown("**Supported Databases:**")
    db_cols = st.columns(len(DB_CONFIGS))
    for i, (dbname, dbconf) in enumerate(DB_CONFIGS.items()):
        with db_cols[i]:
            st.markdown(f"{dbconf['icon']} **{dbname.split(' ', 1)[-1]}**")
