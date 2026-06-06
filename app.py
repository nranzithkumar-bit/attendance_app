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
    try:
        # Using read_csv because the internal file structure is plain-text CSV
        students_df = pd.read_csv("students.xlsx")
        students_df.columns = [str(col).strip().lower().replace(" ", "_") for col in students_df.columns]
        students_df.to_sql("students", conn, if_exists="replace", index=False)
    except Exception as e:
        print(f"Excel sync notice: {e}")

    conn.commit()
    conn.close()


# =====================================================================
# HTML TEMPLATES (ADMIN VIEW & STUDENT PORTAL)
# =====================================================================

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PET Master Panel - Gate Attendance Management</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f7f6; color: #333; }
        .header { background-color: #2c3e50; color: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { margin: 0; font-size: 22px; }
        .domain-tag { font-size: 14px; color: #bdc3c7; background: #34495e; padding: 5px 10px; border-radius: 4px; text-decoration: none; }
        
        .container { display: flex; gap: 20px; flex-wrap: wrap; }
        .panel { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); flex: 1; min-width: 320px; }
        
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #7f8c8d; }
        input[type="text"] { width: 100%; padding: 12px; margin-bottom: 15px; box-sizing: border-box; border: 2px solid #bdc3c7; border-radius: 6px; font-size: 16px; }
        input[type="submit"] { width: 100%; background-color: #2980b9; color: white; padding: 12px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; transition: 0.2s; }
        input[type="submit"]:hover { background-color: #3498db; }
        
        .result-box { margin-top: 20px; padding: 15px; border-radius: 6px; border-left: 6px solid; background-color: #fdfefe; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .info-row { margin: 8px 0; font-size: 15px; }
        .info-row strong { color: #2c3e50; }
        .status-msg { font-size: 18px; font-weight: bold; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ddd; }
        
        .status-1 { border-left-color: #f1c40f; color: #b7950b; }
        .status-2 { border-left-color: #e67e22; color: #d35400; }
        .status-3 { border-left-color: #e74c3c; color: #c0392b; }
        .status-error { border-left-color: #7f8c8d; color: #34495e; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background-color: #f8f9fa; color: #7f8c8d; font-weight: 600; text-transform: uppercase; font-size: 12px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block; }
        .badge-warning { background-color: #fef9e7; color: #f1c40f; }
        .badge-careful { background-color: #fdf2e9; color: #e67e22; }
        .badge-fine { background-color: #fdedec; color: #e74c3c; }
        
        .btn-csv { background-color: #27ae60; color: white; padding: 8px 15px; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: bold; display: inline-block; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Gate Attendance Management (PET Master View)</h1>
        <a href="/student" class="domain-tag" target="_blank">🔗 Open Student Interface</a>
    </div>

    <div class="container">
        <div class="panel">
            <h3>Campus Entry Log</h3>
            <form method="POST" action="/">
                <label for="student_id">Scan/Enter Student ID</label>
                <input type="text" id="student_id" name="student_id" placeholder="e.g., 101" autofocus required>
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
                        <th>ID</th>
                        <th>Student Name</th>
                        <th>Branch</th>
                        <th>Sec</th>
                        <th>Late Days</th>
                        <th>Action Status</th>
                        <th>Last Late Time</th>
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

STUDENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Student Portal - Attendance Check</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 40px; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; min-height: 80vh; }
        .student-panel { background: white; padding: 35px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); width: 100%; max-width: 480px; }
        h2 { margin-top: 0; color: #2c3e50; text-align: center; margin-bottom: 25px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #7f8c8d; }
        input[type="text"] { width: 100%; padding: 14px; margin-bottom: 20px; box-sizing: border-box; border: 2px solid #bdc3c7; border-radius: 8px; font-size: 16px; text-align: center; }
        input[type="submit"] { width: 100%; background-color: #27ae60; color: white; padding: 14px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; transition: 0.2s; }
        input[type="submit"]:hover { background-color: #2ecc71; }
        
        .result-box { margin-top: 25px; padding: 20px; border-radius: 8px; border-left: 6px solid; background-color: #fdfefe; box-shadow: 0 4px 12px rgba(0,0,0,0.04); }
        .info-row { margin: 10px 0; font-size: 15px; border-bottom: 1px dashed #f0f0f0; padding-bottom: 8px; }
        .info-row:last-child { border: none; }
        .info-row strong { color: #7f8c8d; display: inline-block; width: 140px; }
        .status-msg { font-size: 18px; font-weight: bold; margin-top: 15px; padding-top: 12px; border-top: 2px solid #eee; text-align: center; }
        
        .status-1 { border-left-color: #f1c40f; color: #b7950b; }
        .status-2 { border-left-color: #e67e22; color: #d35400; }
        .status-3 { border-left-color: #e74c3c; color: #c0392b; }
        .status-good { border-left-color: #27ae60; color: #27ae60; }
        .status-error { border-left-color: #7f8c8d; color: #34495e; }
    </style>
</head>
<body>
    <div class="student-panel">
        <h2>Campus Attendance Check</h2>
        <form method="POST" action="/student">
            <label for="student_id">Enter Student ID to Check Logs</label>
            <input type="text" id="student_id" name="student_id" placeholder="Type your ID here..." autofocus required>
            <input type="submit" value="View My Attendance History">
        </form>

        {% if result %}
        <div class="result-box {{ result.classname }}">
            {% if result.classname != 'status-error' %}
                <div class="info-row"><strong>Student Name:</strong> <span style="color:#2c3e50; font-weight:bold;">{{ result.name }}</span></div>
                <div class="info-row"><strong>Branch & Section:</strong> {{ result.branch }} - {{ result.section }}</div>
                <div class="info-row"><strong>Total Days Late:</strong> <span style="font-weight:bold;">{{ result.late_days }} Days</span></div>
                {% if result.last_time %}
                    <div class="info-row"><strong>Last Entry Time:</strong> {{ result.last_time }}</div>
                {% endif %}
            {% endif %}
            <div class="status-msg">{{ result.message }}</div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""


# =====================================================================
# CONTROLLER ROUTING LOGIC
# =====================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    """ADMIN PANEL: Handles tracking lookups, daily scans, and logs changes."""
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

        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
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
            cursor.execute("SELECT COUNT(*) FROM late_entries WHERE student_id = ? AND date = ?", (student_id, current_date))
            already_logged = cursor.fetchone()[0]

            if already_logged > 0:
                result = {
                    "student_id": student_id,
                    "time": current_time,
                    "message": "Already entry logged for today!",
                    "classname": "status-error"
                }
            else:
                cursor.execute("SELECT COUNT(*) FROM late_entries WHERE student_id = ?", (student_id,))
                past_strikes = cursor.fetchone()[0]

                # Log fresh daily late records utilizing clean 12 hour AM/PM tags
                cursor.execute("INSERT INTO late_entries (student_id, date, time) VALUES (?, ?, ?)", (student_id, current_date, current_time))
                conn.commit()

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
                    "time": current_time,
                    "message": msg,
                    "classname": cls
                }

            cursor.close()
            conn.close()

    # Load fresh dashboard table datasets
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.student_id, s.student_name, s.branch, s.section, s.phone,
               COUNT(l.student_id) as late_count, MAX(l.time) as last_entry_time
        FROM students s
        LEFT JOIN late_entries l ON s.student_id = l.student_id
        GROUP BY s.student_id, s.student_name, s.branch, s.section, s.phone
        ORDER BY late_count DESC
    """)
    dashboard_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template_string(ADMIN_TEMPLATE, result=result, dashboard_data=dashboard_data)


@app.route('/student', methods=['GET', 'POST'])
def student_portal():
    """STUDENT PORTAL: Allows isolated metrics view for accountability verification."""
    result = None
    if request.method == 'POST':
        student_id = request.form['student_id'].strip()
        try:
            student_id = int(student_id)
        except ValueError:
            pass

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()

        if not student:
            result = {"message": "Invalid Student ID. Verify credentials with PET department.", "classname": "status-error"}
        else:
            cursor.execute("SELECT COUNT(*), MAX(time) FROM late_entries WHERE student_id = ?", (student_id,))
            late_row = cursor.fetchone()
            late_count = late_row[0]
            last_time = late_row[1]

            if late_count == 0:
                msg = "Good Attendance! Keep maintaining punctuality."
                cls = "status-good"
            elif late_count == 1:
                msg = "1st Warning Status Issued."
                cls = "status-1"
            elif late_count == 2:
                msg = "2nd Warning Issued. Immediate parent contact pending."
                cls = "status-2"
            else:
                msg = f"Fine Active: Please settle ₹100 fine structural dues."
                cls = "status-3"

            result = {
                "name": student["student_name"],
                "branch": student["branch"],
                "section": student["section"],
                "late_days": late_count,
                "last_time": last_time,
                "message": msg,
                "classname": cls
            }
        cursor.close()
        conn.close()

    return render_template_string(STUDENT_TEMPLATE, result=result)


@app.route('/export')
def export_excel_csv():
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