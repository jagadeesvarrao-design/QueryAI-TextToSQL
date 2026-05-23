# 🏥 MediQuery AI — Text-to-SQL Data Analyst

> **Ask hospital data questions in plain English. AI converts them to SQL and shows results instantly.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash_/_2.0_Flash-green)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🚀 What This Project Does

MediQuery AI is a **Generative AI-powered web application** that lets you interact with a hospital database using natural language — no SQL knowledge required.

**Example:** You type `"Which doctor has the highest number of appointments?"` → AI generates SQL → Results + chart appear instantly.

## ✨ Features

- 🤖 **Natural Language → SQL** using Google Gemini API (2.5 Flash, 2.0 Flash, 2.0 Flash Lite, 2.5 Pro)
- 📊 **Auto-generated charts** (bar, line, histogram) from query results
- 🏥 **Hospital Database** with 150 patients, 20 doctors, 300 appointments
- 💡 **10 sample questions** to get started instantly
- 🕐 **Query history** panel in sidebar
- ⬇️ **CSV download** for any query result
- 🧠 **SQL transparency** — always shows the generated SQL
- 🌙 **Beautiful dark UI** with glassmorphism design

---

## 🗃️ Database Schema

```
patients       → patient_id, name, age, gender, blood_type, city
doctors        → doctor_id, name, specialization, experience_years, fee
appointments   → appt_id, patient_id, doctor_id, date, status, diagnosis
prescriptions  → pres_id, appt_id, medicine, dosage, duration_days
billing        → bill_id, appt_id, amount, payment_method, paid_date
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/text-to-sql.git
cd text-to-sql
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get your FREE Gemini API key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key

### 4. Create your `.env` file
```bash
cp .env.example .env
```
Open `.env` and replace `your_gemini_api_key_here` with your actual key.

### 5. Run the app
```bash
streamlit run app.py
```

The app automatically creates the hospital database on first run! 🎉

---

## 💬 Example Questions to Try

| Question | What it shows |
|---|---|
| Which doctor has the most appointments? | Doctor performance ranking |
| Show total revenue by payment method | Payment analytics |
| List all patients diagnosed with Diabetes | Diagnosis filtering |
| What is the average billing amount per specialization? | Financial insights |
| How many male vs female patients? | Demographics |
| Top 5 most prescribed medicines | Prescription analytics |
| Which city has the most patients? | Geographic distribution |
| Show patients older than 60 | Age filtering with conditions |

---

## 🏗️ Architecture

```
User Question (plain English)
        ↓
[Gemini API (Dynamic Selection)] ← Database Schema Context
        ↓
   SQL Query
        ↓
  [SQLite DB] → hospital.db
        ↓
 Pandas DataFrame
        ↓
[Streamlit UI] → Table + Plotly Chart
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| AI / LLM | Google Gemini API (2.5 Flash / 2.0 Flash / 2.0 Flash Lite / 2.5 Pro) |
| Web Framework | Streamlit |
| Database | SQLite |
| Data Processing | Pandas |
| Visualization | Plotly Express |
| Environment | python-dotenv |

---

## 📁 Project Structure

```
text-to-sql/
├── app.py                  ← Main Streamlit application
├── requirements.txt        ← Python dependencies
├── .env.example            ← API key template
├── README.md               ← This file
├── database/
│   ├── setup_db.py         ← Database creation & seeding
│   └── hospital.db         ← SQLite database (auto-created)
└── utils/
    ├── db_handler.py       ← DB connection & query execution
    ├── llm_handler.py      ← Gemini API integration
    └── visualizer.py       ← Auto-chart generation
```

---

## 🌟 Resume Highlight

> *"Built an AI-powered Text-to-SQL interface using Google Gemini that converts natural language queries to SQL, enabling non-technical users to analyze any connected database (SQLite, MySQL, PostgreSQL, MSSQL, Oracle, or CSV). Deployed as an interactive Streamlit web app with real-time visualization and dynamic model switching."*

---

## 🤝 Contributing
Pull requests are welcome! For major changes, please open an issue first.

## 📄 License
MIT License — feel free to use this project in your portfolio!
