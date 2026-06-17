# Version 2 - Capitalized Excel Import Fix
import os
import datetime
import pandas as pd  
from flask import Flask, request, render_template_string, Response
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# 📋 The updated active Mumbai transaction connection string
DATABASE_URL = "postgresql://postgres.ujjoynqjmzuurefkapbu:Diet2025%23DIET@aws-1-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"

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
    print("✅ Database initialized successfully!")

def seed_students_from_excel():
    excel_file = "students.xlsx"
    
    if not os.path.exists(excel_file):
        print("❌ CRITICAL: students.xlsx was NOT found in the Render project folder!")
        return

    print("⏳ DETECTED: students.xlsx found! Attempting to read columns...")
    
    try:
        df = pd.read_excel(excel_file)
        # 🔎 This line prints the exact column names the server sees into your logs:
        print(f"📋 ACTUAL EXCEL COLUMNS SEEN BY SERVER: {list(df.columns)}")
        print(f"📊 TOTAL ROWS IN EXCEL SHEET: {len(df)}")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        inserted_count = 0
        for index, row in df.iterrows():
            # Standardizing keys to uppercase to match your strategy
            student_id = str(row.get('STUDENT_ID', '')).strip().upper()
            name = str(row.get('STUDENT_NAME', '')).strip()
            phone = str(row.get('PHONE', '')).strip()

            if not student_id or student_id == 'NAN':
                continue

            cursor.execute('''
                INSERT INTO students (student_id, name, phone) 
                VALUES (%s, %s, %s)
                ON CONFLICT (student_id) DO NOTHING;
            ''', (student_id, name, phone))
            inserted_count += 1
            
        conn.commit()
        print(f"🚀 SUCCESS: Processed {inserted_count} student loops successfully!")
        
    except Exception as e:
        print(f"💥 CRITICAL ERROR DURING EXCEL IMPORT: {str(e)}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# 🌍 RUN ON BOOT (This forces execution on both Local machine and Render server)
init_cloud_db()
seed_students_from_excel()

# ... keep your standard @app.route paths here unchanged ...

if __name__ == '__main__':
    # Local fallback execution fallback engine
    app.run(debug=True)