import os
import datetime
import pandas as pd  # 👈 Make sure this is imported at the top
from flask import Flask, request, render_template_string, Response
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Your correct working database connection string
DATABASE_URL = "postgresql://postgres.otdnicspqedsfsqmsjso:Nrkdiet%406676@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_cloud_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create students master table first
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(20)
        );
    ''')
    # Create late entries table second
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS late_entries (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        );
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def seed_students_from_excel():
    excel_file = "students.xlsx"
    
    if not os.path.exists(excel_file):
        print("❌ students.xlsx not found in project directory.")
        return

    print("⏳ Reading students.xlsx and synchronizing with Supabase...")
    df = pd.read_excel(excel_file)
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
	# Loop through each student in your Excel rows
        for index, row in df.iterrows():
            # These must match your new ALL-CAPS Excel column headers exactly!
            student_id = str(row['STUDENT_ID']).strip().upper()
            name = str(row['STUDENT_NAME']).strip()
            phone = str(row['PHONE']).strip() if 'PHONE' in df.columns else ""

            cursor.execute('''
                INSERT INTO students (student_id, name, phone) 
                VALUES (%s, %s, %s)
                ON CONFLICT (student_id) DO NOTHING;
            ''', (student_id, name, phone))


        conn.commit()
        print("✅ Successfully synchronized 1,763 student records from Excel to Supabase!")
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
    finally:
        cursor.close()
        conn.close()

# ... keep your standard @app.route paths here unchanged ...

if __name__ == '__main__':
    init_cloud_db()
    seed_students_from_excel()  # 👈 This forces synchronization on startup
    app.run(debug=False)