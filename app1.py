# this code is from app.py for backup code

import pandas as pd
import sqlite3
import datetime
from flask import Flask, request, render_template_string, Response

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect("attendance.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS late_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)

    # Read Excel Data
    students_df = pd.read_excel("students.xlsx")

    # CRITICAL FIX: Strips whitespace and forces all column headers (like 'Phone') to lowercase
    students_df.columns = [str(col).strip().lower().replace(" ", "_") for col in students_df.columns]

    # Import normalized Excel structures into SQLite
    students_df.to_sql(
        "students",
        conn,
        if_exists="replace",
        index=False
    )

    conn.commit()
    conn.close()


# HTML & CSS Interface styled exactly like your Dashboard Wireframe sketch
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Late Students Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f7f6; color: #333; }
        .header { background-color: #2c3e50; color: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { margin: 0; font-size: 22px; }
        .domain-tag { font-size: 14px; color: #bdc3c7; background: #34495e; padding: 5px 10px; border-radius: 4px; }
        
        .container { display: flex; gap: 20px; flex-wrap: wrap; }
        .panel { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); flex: 1; min-width: 320px; }
        
        /* Form & Result Styling */
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #7f8c8d; }
        input[type="text"] { width: 100%; padding: 12px; margin-bottom: 15px; box-sizing: border-box; border: 2px solid #bdc3c7; border-radius: 6px; font-size: 16px; }
        input[type="submit"] { width: 100%; background-color: #2980b9; color: white; padding: 12px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; transition: 0.2s; }
        input[type="submit"]:hover { background-color: #3498db; }
        
        /* Dynamic Popup Result Box based on your sketch */
        .result-box { margin-top: 20px; padding: 15px; border-radius: 6px; border-left: 6px solid; background-color: #fdfefe; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .info-row { margin: 8px 0; font-size: 15px; }
        .info-row strong { color: #2c3e50; }
        .status-msg { font-size: 18px; font-weight: bold; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ddd; }
        
        /* Status Color Classes */
        .status-1 { border-left-color: #f1c40f; color: #b7950b; } /* Warning */
        .status-2 { border-left-color: #e67e22; color: #d35400; } /* Be Careful */
        .status-3 { border-left-color: #e74c3c; color: #c0392b; } /* Fine ₹100 */
        .status-error { border-left-color: #7f8c8d; color: #34495e; }
        
        /* Table Dashboard Styling */
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background-color: #f8f9fa; color: #7f8c8d; font-weight: 600; text-transform: uppercase; font-size: 12px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block; }
        .badge-warning { background-color: #fef9e7; color: #f1c40f; }
        .badge-careful { background-color: #fdf2e9; color: #e67e22; }
        .badge-fine { background-color: #fdedec; color: #e74c3c; animation: flash 2s infinite; }
        
        .btn-csv { background-color: #27ae60; color: white; padding: 8px 15px; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: bold; display: inline-block; }
        .btn-csv:hover { background-color: #2ecc71; }
        @keyframes flash { 50% { opacity: 0.8; } }
    </style>
</head>
<body>

    <div class="header">
        <h1>Gate Attendance Management</h1>
        <div class="domain-tag">www.professionalbird.com Dashboard</div>
    </div>

    <div class="container">
        <div class="panel">
            <h3>Campus Entry Log</h3>
            <form method="POST" action="/">
                <label for="student_id">Scan/Enter Student ID</label>
                <input type="text" id="student_id" name="student_id" placeholder="e.g., XY347" autofocus required>
                <input type="submit" value="Log Entry & Verify">
            </form>

            {% if result %}
            <div class="result-box {{ result.classname }}">
                <div class="info-row"><strong>Campus Entering Time:</strong> {{ result.time }}</div>
                <div class="info-row"><strong>Student ID:</strong> {{ result.student_id }}</div>
                <div class="status-msg">{{ result.message }}</div>
            </div>
            {% endif %}
        </div>

        <div class="panel" style="flex: 1.5;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0;">Continuous Late Comers Tracker</h3>
                <a href="/export" class="btn-csv">📥 Download Excel/CSV</a>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Student ID</th>
                        <th>Student Name</th>
                        <th>Branch</th>
                        <th>Section</th>
                        <th>Total days late</th>
                        <th>Action Status</th>
                        <th>Campus Entering Time</th>
                        <th>Phone</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in dashboard_data %}
                    <tr>
                        <td><strong>{{ row.student_id }}</strong></td>
                        <td>{{ row.student_name }}</td>
                        <td>{{ row.branch }}</td>
                        <td>{{ row.section }}</td>
                        <td>{{ row.late_count }} Days</td>
                        <td>    
                            {% if row.late_count == 0 %}
                                <span class="badge">Good Attendance</span>
                            {% elif row.late_count == 1 %}
                                <span class="badge badge-warning">1st Warning</span>
                            {% elif row.late_count == 2 %}
                                <span class="badge badge-careful">2nd Warning</span>
                            {% else %}
                                <span class="badge badge-fine">Pay ₹100 Fine</span>
                            {% endif %}
                        </td>
                        <td>{{ row.last_entry_time if row.last_entry_time else 'N/A' }}</td>
                        <td>{{ row.phone if row.phone else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    now = datetime.datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%I:%M %p") 

    if request.method == 'POST':
        student_id = request.form['student_id'].strip()
        try:
            student_id = int(student_id)
        except ValueError:
            pass

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id,)
        )
        student = cursor.fetchone()

        if not student:
            result = {
                "student_id": student_id,
                "time": current_time,
                "message": "Invalid Student ID",
                "classname": "status-error"
            }
            cursor.close()
            conn.close()
        else:
            # 1. Protection Check: Prevent scanning the same student twice on the same day
            cursor.execute(
                "SELECT COUNT(*) FROM late_entries WHERE student_id = ? AND date = ?",
                (student_id, current_date)
            )
            already_logged = cursor.fetchone()[0]

            if already_logged > 0:
                result = {
                    "student_id": student_id,
                    "time": current_time,
                    "message": "Already entry logged for today!",
                    "classname": "status-error"
                }
            else:
                # 2. Look up historical records to apply business rules
                cursor.execute(
                    "SELECT COUNT(*) FROM late_entries WHERE student_id = ?",
                    (student_id,)
                )
                past_strikes = cursor.fetchone()[0]

                # 3. Log today's entry
                cursor.execute(
                    "INSERT INTO late_entries (student_id, date, time) VALUES (?, ?, ?)",
                    (student_id, current_date, current_time)
                )
                conn.commit()

                # 4. Pure Execution Logic based on your requirements
                current_strike_total = past_strikes + 1

                if current_strike_total == 1:
                    msg = "1st time late – Warning"
                    cls = "status-1"
                elif current_strike_total == 2:
                    msg = "2nd time late – Be careful"
                    cls = "status-2"
                else:
                    msg = f"3rd time late (Total: {current_strike_total}) – Pay ₹100"
                    cls = "status-3"

                result = {
                    "student_id": student["student_id"],
                    "Name": student["student_name"],
                    "Branch": student["branch"],
                    "Section": student["section"],
                    "Phone": student["phone"],
                    "time": current_time,
                    "message": msg,
                    "classname": cls
                }

            cursor.close()
            conn.close()

    # Always reload fresh dashboard table lists
    conn = get_db_connection()
    cursor = conn.cursor()
        
    # FIX: Selects s.phone and MAX(l.time) to fill the empty columns correctly
    cursor.execute("""
        SELECT
            s.student_id,
            s.student_name,
            s.branch,
            s.section,
            s.phone,
            COUNT(l.student_id) as late_count,
            MAX(l.time) as last_entry_time
        FROM students s
        LEFT JOIN late_entries l
            ON s.student_id = l.student_id
        GROUP BY
            s.student_id,
            s.student_name,
            s.branch,
            s.section,
            s.phone
        ORDER BY late_count DESC
    """)
      
    dashboard_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template_string(DASHBOARD_TEMPLATE, result=result, dashboard_data=dashboard_data)

@app.route('/export')
def export_excel_csv():
    """Compiles all records and streams a clean Excel-compatible CSV file instantly"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, date, time FROM late_entries ORDER BY date DESC, time DESC")
    records = cursor.fetchall()
    cursor.close()
    conn.close()

    csv_output = "Student ID,Date,Time Locked\n"
    for row in records:
        csv_output += f"{row['student_id']},{row['date']},{row['time']}\n"

    return Response(
        csv_output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=late_records_{datetime.datetime.now().strftime('%Y-%m-%d')}.csv"}
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True)