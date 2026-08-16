# 🧠 QueryAI — Universal Text-to-SQL AI Data Analyst

> **Talk to your database in plain English. Powered by Google Gemini, SQLAlchemy, and Streamlit.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-ff4b4b.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash_/_2.5_Pro-blueviolet.svg?logo=google-gemini&logoColor=white)](https://aistudio.google.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

**QueryAI** is an advanced Generative AI-powered web application that acts as a natural language interface for databases. It enables non-technical users to query database servers, upload CSV data, or analyze pre-seeded mock records by typing questions in plain English—no SQL knowledge required.

QueryAI dynamically parses active schemas, translates human queries into optimized database-specific dialect statements (SQLite, MySQL, PostgreSQL, MS SQL Server, or Oracle SQL), executes them safely, displays interactive tabular results, and automatically determines and styles beautiful Plotly visualizations matching a premium dark glassmorphism dashboard theme.

---

## ✨ Outstanding Features

- 🤖 **Universal Text-to-SQL**: Auto-detects the active database dialect (MySQL, PostgreSQL, MS SQL, Oracle, SQLite) and structures the translation context accordingly.
- 🎯 **Semantic Schema Pruning (Schema RAG)**: Vectorizes table definitions using embeddings and performs cosine similarity search against user queries to scale seamlessly to **150+ tables** while eliminating LLM token bloat.
- 📊 **Smart Auto-Visualization**: Intelligently inspects query result sets to choose, build, and style Plotly graphs (Bar, Line, Histograms, or Frequency Count charts).
- 📄 **Dynamic CSV Uploads**: Drag and drop multiple CSV sheets to instantly query them as virtual relational tables in-memory.
- 🏥 **Out-of-the-Box Demo**: Instantly provisions a mock hospital database with 150 patients, 20 doctors, and 300 appointments to experience the app in 1 click.
- 🔌 **Secure Connection Manager**: Supports custom connection parameters (e.g. SSL rules like `TrustServerCertificate=yes` or `sslmode=require`).
- 🤖 **AI Model Resiliency**: Multi-model fallback configuration (`gemini-2.5-flash`, `gemini-2.0-flash-lite`, `gemini-2.5-pro`) to ensure high availability.
- 🕐 **Analyst Audit Trace**: Transparently displays generated SQL alongside latency logs, row counts, and detailed column type schemas.

---

## 🏗️ Architecture & Processing Lifecycle

```mermaid
graph TD
    User([User English Question]) --> UI[Streamlit Frontend]
    UI --> Pruner[utils/schema_pruner.py (Schema RAG)]
    DbConn[(Target Database)] -->|Reflect Schema 150+ Tables| Pruner
    Pruner -->|Vector Cosine Lookup & Pruning| PrunedSchema[Top-K Relevant Table Schemas]
    
    PrunedSchema --> LLM[utils/llm_handler.py]
    User -.-> LLM
    LLM -->|Prompt Injection| Gemini[Google Gemini API]
    
    Gemini -->|Returns Raw SQL| LLM
    LLM -->|Clean SQL| UI
    UI --> DB[utils/connection_manager.py]
    DB -->|Execute SQL| DbConn
    DbConn -->|Retrieve Data| DB
    DB -->|Pandas DataFrame| UI
    
    %% Visual outputs
    UI --> Table[Interactive Data Table]
    UI --> Chart[Plotly Auto-Visualization]
```

---

## 🗃️ Supported Databases

| Engine | Driver Package | Default Port | Connection URL Format |
| :--- | :--- | :--- | :--- |
| **🏥 Demo SQLite** | *None (Built-in)* | *None* | `sqlite:///database/hospital.db` |
| **📄 CSV Upload** | *None (Pandas)* | *None* | `sqlite:///:memory:` |
| **📁 SQLite File** | *None (Built-in)* | *None* | `sqlite:///path/to/database.db` |
| **🐬 MySQL** | `pymysql` | `3306` | `mysql+pymysql://user:pass@host:port/database` |
| **🐘 PostgreSQL** | `psycopg2-binary` | `5432` | `postgresql+psycopg2://user:pass@host:port/database` |
| **🪟 SQL Server** | `pymssql` | `1433` | `mssql+pymssql://user:pass@host:port/database` |
| **🔴 Oracle SQL** | `oracledb` | `1521` | `oracle+oracledb://user:pass@host:port/database` |

---

## 🚀 Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/QueryAI-TextToSQL.git
cd QueryAI-TextToSQL
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Get your Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key

### 4. Create your `.env` File
```bash
cp .env.example .env
```
Open `.env` and assign your actual key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Launch the Application
```bash
streamlit run app.py
```
The app will automatically compile the local hospital database on first run and launch the browser panel! 🎉

---

## 🧪 Comprehensive Verification Tests

The repository is equipped with two testing modules to validate all components under different environments:

### 1. Unit & Module Integration Tests
Verifies local database builds, column mapping schemas, in-memory CSV connections, and Plotly layout generators:
```bash
python test_all.py
```

### 2. End-to-End Simulation Tests
Mocks the Streamlit framework to virtually test session states, database selector resets, and dialect-specific translation prompts:
```bash
python test_website_flow.py
```

---

## 📖 Setup Walkthrough Reference
For step-by-step credentials setups, SSL configurations, driver installation checklists, and firewalls troubleshooting for each database engine, view the walkthrough guide:
* 📁 [Database Setup Walkthrough](database_setup_walkthrough.md)

---

## 📄 License
This project is licensed under the MIT License — feel free to use it in your portfolio or modify it for your own systems!
