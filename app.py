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
    
    # Try reading and parsing local Excel data to Supabase
    try:
        import pandas as pd
        if os.path.exists("students.xlsx"):
            students_df = pd.read_excel("students.xlsx")
            
            # Clean column strings to handle variations gracefully
            students_df.columns = [str(col).strip().lower().replace(" ", "_") for col in students_df.columns]
            
            # Identify the unique identifier column
            id_col = None
            for col in students_df.columns:
                if col in ['student_id', 'roll_no', 'regd_no', 'pin', 'id', 'admission_no', 'rollno', 'regdno']:
                    id_col = col
                    break
            
            if id_col:
                students_df = students_df.rename(columns={id_col: 'student_id'})
                print(f"✅ Dynamic Mapper: Using '{id_col}' as core 'student_id'")
            else:
                print("⚠️ System Warning: No explicit ID column found in Excel file.")
            
            # Re-create the students reference table on Supabase
            cursor.execute("DROP TABLE IF EXISTS students CASCADE;")
            
            # Dynamically compile the CREATE TABLE columns based on Excel structure
            columns_schema = ", ".join([f"{col} TEXT" for col in students_df.columns if col != 'student_id'])
            create_query = f"CREATE TABLE students (student_id TEXT PRIMARY KEY, {columns_schema});"
            cursor.execute(create_query)
            
            # Stream rows up to Supabase using bulk insert formatting
            for _, row in students_df.iterrows():
                row_dict = row.to_dict()
                cols = list(row_dict.keys())
                vals = [str(row_dict[c]).strip() if pd.notnull(row_dict[c]) else "" for c in cols]
                
                placeholders = ", ".join(["%s"] * len(cols))
                insert_query = f"INSERT INTO students ({', '.join(cols)}) VALUES ({placeholders}) ON CONFLICT (student_id) DO NOTHING;"
                cursor.execute(insert_query, vals)
                
            print("🚀 Supabase Database initialized and students records synced cleanly!")
        else:
            print("ℹ️ Note: students.xlsx not detected locally. Using existing cloud architecture.")
    except Exception as e:
        print(f"Excel sync notice: {e}")
        
    conn.commit()
    cursor.close()
    conn.close()

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