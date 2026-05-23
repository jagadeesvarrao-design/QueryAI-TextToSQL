"""
setup_db.py — Creates and seeds the hospital SQLite database.
Run once: python database/setup_db.py
"""
import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "hospital.db")

# ─── Seed Data ─────────────────────────────────────────────────────────────────

FIRST_NAMES = ["Aarav", "Priya", "Rohan", "Sneha", "Kiran", "Meera",
               "Arjun", "Pooja", "Vikram", "Ananya", "Rahul", "Neha",
               "Aditya", "Kavya", "Siddharth", "Divya", "Rajesh", "Sunita",
               "Manoj", "Lakshmi", "Deepak", "Geeta", "Suresh", "Rekha",
               "Amit", "Sonal", "Harish", "Nisha", "Vinod", "Rupa"]

LAST_NAMES = ["Sharma", "Patel", "Verma", "Singh", "Kumar", "Gupta",
              "Joshi", "Nair", "Mehta", "Rao", "Mishra", "Reddy",
              "Shah", "Kapoor", "Malhotra", "Bose", "Iyer", "Pillai",
              "Das", "Ghosh", "Pandey", "Jain", "Agarwal", "Srivastava"]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad",
          "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
          "Chandigarh", "Bhopal", "Surat", "Nagpur", "Indore"]

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

SPECIALIZATIONS = ["Cardiology", "Neurology", "Orthopedics", "Dermatology",
                   "Pediatrics", "General Medicine", "Oncology", "ENT",
                   "Ophthalmology", "Gastroenterology"]

DIAGNOSES = ["Hypertension", "Diabetes Type 2", "Migraine", "Asthma",
             "Arthritis", "Pneumonia", "Fracture", "Anemia",
             "Thyroid Disorder", "Dengue Fever", "Typhoid", "COVID-19",
             "Kidney Stone", "Appendicitis", "Gastritis", "Eczema",
             "Cataract", "Bronchitis", "Sinusitis", "Back Pain"]

STATUSES = ["Completed", "Completed", "Completed", "Cancelled", "Pending"]

MEDICINES = ["Paracetamol", "Amoxicillin", "Metformin", "Atorvastatin",
             "Omeprazole", "Aspirin", "Lisinopril", "Amlodipine",
             "Cetirizine", "Azithromycin", "Pantoprazole", "Ibuprofen",
             "Dolo 650", "Crocin", "Vitamin D3", "Calcium Supplement"]

DOSAGES = ["500mg once daily", "250mg twice daily", "10mg at night",
           "5mg morning", "20mg before meals", "100mg twice daily",
           "1 tablet daily", "2 tablets daily"]

PAYMENT_METHODS = ["Cash", "Credit Card", "Debit Card", "UPI", "Insurance"]


def random_date(start_days_ago=730, end_days_ago=0):
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    return (start + (end - start) * random.random()).strftime("%Y-%m-%d")


def setup_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Create Tables ──────────────────────────────────────────────────────────
    cur.executescript("""
        CREATE TABLE patients (
            patient_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            age          INTEGER,
            gender       TEXT,
            blood_type   TEXT,
            city         TEXT
        );

        CREATE TABLE doctors (
            doctor_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name               TEXT NOT NULL,
            specialization     TEXT,
            experience_years   INTEGER,
            fee                INTEGER
        );

        CREATE TABLE appointments (
            appt_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id  INTEGER REFERENCES patients(patient_id),
            doctor_id   INTEGER REFERENCES doctors(doctor_id),
            date        TEXT,
            status      TEXT,
            diagnosis   TEXT
        );

        CREATE TABLE prescriptions (
            pres_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            appt_id        INTEGER REFERENCES appointments(appt_id),
            medicine       TEXT,
            dosage         TEXT,
            duration_days  INTEGER
        );

        CREATE TABLE billing (
            bill_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            appt_id         INTEGER REFERENCES appointments(appt_id),
            amount          INTEGER,
            payment_method  TEXT,
            paid_date       TEXT
        );
    """)

    # ── Seed Patients (150) ───────────────────────────────────────────────────
    patients = []
    for i in range(150):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        age = random.randint(5, 85)
        gender = random.choice(["Male", "Female", "Female", "Male"])
        blood_type = random.choice(BLOOD_TYPES)
        city = random.choice(CITIES)
        patients.append((name, age, gender, blood_type, city))
    cur.executemany(
        "INSERT INTO patients (name, age, gender, blood_type, city) VALUES (?,?,?,?,?)",
        patients
    )

    # ── Seed Doctors (20) ─────────────────────────────────────────────────────
    doctors = []
    for i in range(20):
        name = f"Dr. {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        spec = random.choice(SPECIALIZATIONS)
        exp = random.randint(2, 35)
        fee = random.choice([300, 500, 700, 800, 1000, 1200, 1500, 2000])
        doctors.append((name, spec, exp, fee))
    cur.executemany(
        "INSERT INTO doctors (name, specialization, experience_years, fee) VALUES (?,?,?,?)",
        doctors
    )

    # ── Seed Appointments (300) ───────────────────────────────────────────────
    appointments = []
    for i in range(300):
        p_id = random.randint(1, 150)
        d_id = random.randint(1, 20)
        date = random_date(730, 0)
        status = random.choice(STATUSES)
        diagnosis = random.choice(DIAGNOSES)
        appointments.append((p_id, d_id, date, status, diagnosis))
    cur.executemany(
        "INSERT INTO appointments (patient_id, doctor_id, date, status, diagnosis) VALUES (?,?,?,?,?)",
        appointments
    )

    # ── Seed Prescriptions (1–2 per completed appointment) ───────────────────
    cur.execute("SELECT appt_id FROM appointments WHERE status='Completed'")
    completed_appts = [row[0] for row in cur.fetchall()]
    prescriptions = []
    for appt_id in completed_appts:
        for _ in range(random.randint(1, 2)):
            med = random.choice(MEDICINES)
            dosage = random.choice(DOSAGES)
            days = random.choice([3, 5, 7, 10, 14, 30])
            prescriptions.append((appt_id, med, dosage, days))
    cur.executemany(
        "INSERT INTO prescriptions (appt_id, medicine, dosage, duration_days) VALUES (?,?,?,?)",
        prescriptions
    )

    # ── Seed Billing (for completed appointments) ─────────────────────────────
    billing = []
    for appt_id in completed_appts:
        # Fee + medicine cost
        amount = random.randint(300, 5000)
        method = random.choice(PAYMENT_METHODS)
        paid_date = random_date(700, 0)
        billing.append((appt_id, amount, method, paid_date))
    cur.executemany(
        "INSERT INTO billing (appt_id, amount, payment_method, paid_date) VALUES (?,?,?,?)",
        billing
    )

    conn.commit()
    conn.close()

    print(f"[OK] Database created at: {DB_PATH}")
    print(f"     150 patients, 20 doctors, 300 appointments")
    print(f"     {len(prescriptions)} prescriptions, {len(billing)} billing records")


if __name__ == "__main__":
    setup_database()
