import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Fetch the secure database connection string from Render's environment settings
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Establishes a connection to the Supabase PostgreSQL database."""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Supabase Connection Error: {e}")
        return None

def init_db():
    """Initializes tables on Supabase and syncs data from students.xlsx if available."""
    conn = get_db_connection()
    if not conn:
        print("⚠️ Skipping database initialization: Connection unavailable.")
        return
        
    cursor = conn.cursor()
    
    # Create Late Entries tracking table using PostgreSQL syntax
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


# ==================================
# PUT student_count HERE
# ==================================
@app.route('/student_count')
def student_count():
    conn = get_db_connection()

    if not conn:
        return "Database connection failed"

    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()

    cursor.close()
    conn.close()

    return str(count)














@app.route('/', methods=['GET'])
def index():
    """Renders the dashboard metrics panel pulling direct data from Supabase."""
    conn = get_db_connection()
    entries = []
    if conn:
        cursor = conn.cursor()
        # PostgreSQL syntax query combining records
        cursor.execute('''
            SELECT le.student_id, s.student_name, s.branch, s.sec,
                   COUNT(le.id) as late_days,
                   MAX(le.time) as last_late_time,
                   s.phone
            FROM late_entries le
            LEFT JOIN students s ON CAST(le.student_id AS TEXT) = CAST(s.student_id AS TEXT)
            GROUP BY le.student_id, s.student_name, s.branch, s.sec, s.phone
        ''')
        entries = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('index.html', entries=entries)

@app.route('/log_attendance', methods=['POST'])
def log_attendance():
    """API endpoint triggered by frontend JavaScript to check and save student entries."""
    data = request.get_json() or {}
    student_id = str(data.get('student_id', '')).strip()
    
    if not student_id:
        return jsonify({"success": False, "message": "Please enter or scan a Student ID."}), 400
        
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Cloud database connection error."}), 500
        
    cursor = conn.cursor()
    
    # Query Supabase using PostgreSQL parameters (%s instead of SQLite ?)
    cursor.execute("SELECT * FROM students WHERE CAST(student_id AS TEXT) = %s", (student_id,))
    student = cursor.fetchone()
    
    if student:
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%I:%M %p')
        
        # Log entry to database
        cursor.execute(
            "INSERT INTO late_entries (student_id, date, time) VALUES (%s, %s, %s)",
            (student_id, date_str, time_str)
        )
        conn.commit()
        
        response_data = {
            "success": True,
            "message": "Attendance logged successfully!",
            "student_info": dict(student)
        }
    else:
        response_data = {
            "success": False,
            "message": "Invalid Student ID. Record not found."
        }
        
    cursor.close()
    conn.close()
    return jsonify(response_data)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)