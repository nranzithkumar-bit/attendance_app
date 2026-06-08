import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response
import openpyxl

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        print("⚠️ Skipping init: No connection.")
        return
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            branch TEXT,
            section TEXT,
            phone TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS late_entries (
            id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database initialized successfully!")

# Run on startup
init_db()

# =====================================================================
# ROUTES
# =====================================================================

@app.route('/', methods=['GET'])
def index():
    conn = get_db_connection()
    entries = []
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT le.student_id, s.student_name, s.branch, s.section,
                   COUNT(le.id) as late_days,
                   MAX(le.time) as last_late_time,
                   s.phone
            FROM late_entries le
            LEFT JOIN students s ON le.student_id = s.student_id
            GROUP BY le.student_id, s.student_name, s.branch, s.section, s.phone
            ORDER BY late_days DESC
        ''')
        entries = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('index.html', entries=entries)


@app.route('/log_attendance', methods=['POST'])
def log_attendance():
    data = request.get_json() or {}
    student_id = str(data.get('student_id', '')).strip()

    if not student_id:
        return jsonify({"success": False, "message": "Please enter a Student ID."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection error."}), 500

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()

    if student:
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%I:%M %p')

        # Check already logged today
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM late_entries WHERE student_id = %s AND date = %s",
            (student_id, date_str)
        )
        already = cursor.fetchone()["cnt"]

        if already > 0:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "message": f"⚠️ {student['student_name']} already logged today!"
            })

        cursor.execute(
            "INSERT INTO late_entries (student_id, date, time) VALUES (%s, %s, %s)",
            (student_id, date_str, time_str)
        )
        conn.commit()

        # Count total late days
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM late_entries WHERE student_id = %s",
            (student_id,)
        )
        total = cursor.fetchone()["cnt"]

        if total == 1:
            status = "1st Warning issued"
        elif total == 2:
            status = "2nd Warning — Be careful!"
        else:
            status = f"Pay ₹100 Fine (Total: {total} times)"

        response_data = {
            "success": True,
            "message": f"✅ Entry logged! {status}",
            "student_info": dict(student)
        }
    else:
        response_data = {
            "success": False,
            "message": "❌ Invalid Student ID. Not found."
        }

    cursor.close()
    conn.close()
    return jsonify(response_data)


@app.route('/import-students')
def import_students():
    secret = request.args.get("key", "")
    if secret != "diet2025":
        return "Unauthorized", 403
    try:
        wb = openpyxl.load_workbook("students.xlsx")
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        headers = [str(h).strip().lower() for h in rows[0]]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students")

        count = 0
        for row in rows[1:]:
            data = dict(zip(headers, row))
            sid = str(data.get('student_id', '')).strip()
            if not sid or sid == 'None':
                continue
            cursor.execute("""
                INSERT INTO students (student_id, student_name, branch, section, phone)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (student_id) DO UPDATE SET
                    student_name = EXCLUDED.student_name,
                    branch = EXCLUDED.branch,
                    section = EXCLUDED.section,
                    phone = EXCLUDED.phone
            """, (
                sid,
                str(data.get('student_name', '')),
                str(data.get('branch', '')),
                str(data.get('section', '')),
                str(data.get('phone', ''))
            ))
            count += 1

        conn.commit()
        cursor.close()
        conn.close()
        return f"✅ {count} students imported successfully!"
    except Exception as e:
        return f"❌ Error: {e}", 500


@app.route('/export')
def export_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.student_id, s.student_name, s.branch, s.section, l.date, l.time
        FROM late_entries l
        JOIN students s ON l.student_id = s.student_id
        ORDER BY l.date DESC, l.time DESC
    """)
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    csv_output = "Student ID,Student Name,Branch,Section,Date,Time\n"
    for row in records:
        csv_output += f"{row['student_id']},{row['student_name']},{row['branch']},{row['section']},{row['date']},{row['time']}\n"
    return Response(csv_output, mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=late_records_{datetime.now().strftime('%Y-%m-%d')}.csv"})


@app.route('/student_count')
def student_count():
    conn = get_db_connection()
    if not conn:
        return "DB error"
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM students")
    count = cursor.fetchone()["cnt"]
    cursor.close()
    conn.close()
    return f"Total students in database: {count}"


if __name__ == '__main__':
    app.run(debug=True)
