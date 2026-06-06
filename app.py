import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
DATABASE = 'attendance.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS late_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    try:
        import pandas as pd
        students_df = pd.read_excel("students.xlsx")
        students_df.columns = [str(col).strip().lower().replace(" ", "_") for col in students_df.columns]
        
        # SMART MAPPING
        id_col = None
        for col in students_df.columns:
            if col in ['student_id', 'roll_no', 'regd_no', 'pin', 'id', 'admission_no', 'rollno', 'regdno']:
                id_col = col
                break
        if id_col:
            students_df = students_df.rename(columns={id_col: 'student_id'})
            print(f"Mapped Excel column '{id_col}' directly to database 'student_id'")
        students_df.to_sql("students", conn, if_exists="replace", index=False)
        print("Database initialized and students table populated successfully!")
    except Exception as e:
        print(f"Excel sync notice: {e}")
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    message = None
    student_info = None
    
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        
        # Match both string or standard integer type formats
        cursor.execute("SELECT * FROM students WHERE student_id = ? OR student_id = ?", (student_id, str(student_id)))
        student = cursor.fetchone()
        
        if student:
            student_info = dict(student)
            now = datetime.now()
            date_str = now.strftime('%Y-%m-%d')
            time_str = now.strftime('%I:%M %p')
            
            cursor.execute("INSERT INTO late_entries (student_id, date, time) VALUES (?, ?, ?)", (str(student_id), date_str, time_str))
            conn.commit()
            message = "Attendance logged successfully!"
        else:
            message = "Invalid Student ID"
            
    cursor.execute('''
        SELECT le.student_id, s.student_name, s.branch, s.sec,
               COUNT(le.id) as late_days,
               MAX(le.time) as last_late_time,
               s.phone
        FROM late_entries le
        JOIN students s ON str(le.student_id) = str(s.student_id)
        GROUP BY le.student_id
    ''')
    entries = cursor.fetchall()
    conn.close()
    return render_template('index.html', entries=entries, message=message, student_info=student_info)

@app.route('/student', methods=['GET', 'POST'])
def student_view():
    student_history = []
    student_info = None
    message = None
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = ? OR student_id = ?", (student_id, str(student_id)))
        student = cursor.fetchone()
        if student:
            student_info = dict(student)
            cursor.execute("SELECT date, time FROM late_entries WHERE student_id = ? ORDER BY id DESC", (str(student_id),))
            student_history = cursor.fetchall()
        else:
            message = "No records found for this Student ID"
        conn.close()
    return render_template('student.html', student_history=student_history, student_info=student_info, message=message)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
