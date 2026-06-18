import os
import datetime
import pandas as pd  
from flask import Flask, request, render_template_string, jsonify, Response
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# 📋 The updated active Mumbai transaction connection string (with %23 for '#' encoding)
DATABASE_URL = "postgresql://postgres.ujjoynqjmzuurefkapbu:Diet2025%23DIET@aws-1-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_cloud_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 🌟 Added branch and section columns to the database schema explicitly
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id VARCHAR(50) PRIMARY KEY,
            student_name VARCHAR(100) NOT NULL,
            student_phone VARCHAR(20),
            branch VARCHAR(50),
            section VARCHAR(50)
        );
    ''')
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
    print("Base dados inicializada com sucesso!")


def seed_students_from_excel():
    excel_file = "students.xlsx"
    
    if not os.path.exists(excel_file):
        print("❌ CRITICAL: students.xlsx was NOT found!")
        return

    print("⏳ DETECTED: students.xlsx found! Attempting to read columns...")
    
    try:
        df = pd.read_excel(excel_file)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        inserted_count = 0
        for index, row in df.iterrows():
            student_id = str(row.get('STUDENT_ID', '')).strip().upper()
            student_name = str(row.get('STUDENT_NAME', '')).strip()
            phone = str(row.get('PHONE', row.get('STUDENT_PHONE', ''))).strip()
            branch = str(row.get('BRANCH', '')).strip()
            section = str(row.get('SECTION', '')).strip()

            if not student_id or student_id == 'NAN':
                continue

            # 🎯 Inserts new students OR updates Branch/Section for existing ones
            cursor.execute('''
                INSERT INTO students (student_id, student_name, student_phone, branch, section) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (student_id) 
                DO UPDATE SET branch = EXCLUDED.branch, section = EXCLUDED.section;
            ''', (student_id, student_name, phone, branch, section))
            inserted_count += 1
            
        conn.commit()
        print(f"🚀 SUCCESS: Processed {inserted_count} student loops with Branch/Section values!")
        
    except Exception as e:
        print(f"💥 CRITICAL ERROR DURING EXCEL IMPORT: {str(e)}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()


# 🌍 RUN ON BOOT (Forces execution on both local terminal and Render production server instance)
init_cloud_db()
seed_students_from_excel()


# --------------------------------------------------------------------------------------
# HTML UI TEMPLATE STRING (Combines layout, table rendering, and scanner scripts)
# --------------------------------------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DIET Attendance Management System</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css">
    <style>
        body { background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .navbar-brand { font-weight: bold; font-size: 1.5rem; letter-spacing: 0.5px; }
        .card { border: none; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .table th { background-color: #f8f9fa; color: #495057; font-weight: 600; text-transform: uppercase; font-size: 0.8rem; }
        .badge-warning { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
        .badge-danger { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .badge-success { background-color: #d1e7dd; color: #0f5132; }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark bg-primary shadow-sm mb-4">
    <div class="container-fluid px-4">
        <div>
            <a class="navbar-brand d-block" href="#">DIET ATTENDANCE MANAGEMENT SYSTEM</a>
            <small class="text-white-50">Dhanekula Institute of Engineering and Technology, Vijayawada</small>
        </div>
        <div class="d-flex gap-2">
            <button class="btn btn-success fw-semibold btn-sm px-3" onclick="window.location.reload();">🔄 Refresh Page</button>
            <a href="#" class="btn btn-light fw-semibold btn-sm px-3 text-primary">🏠 Main Entrance Gate</a>
        </div>
    </div>
</nav>

<div class="container-fluid px-4">
    <div class="row g-4">
        <div class="col-md-4">
            <div class="card p-4">
                <h5 class="fw-bold mb-3 text-secondary">📋 Log Late Entry</h5>
                <form id="attendance-form" onsubmit="return false;">
                    <label class="form-label text-muted fw-semibold small">SCAN BARCODE OR TYPE STUDENT ID</label>
                    <input type="text" id="student_id" name="student_id" class="form-control form-control-lg border-primary mb-3" placeholder="Enter Roll Number / ID..." autofocus required autocomplete="off">
                    <button type="submit" class="btn btn-primary btn-lg w-100 fw-bold">Log Entry & Verify</button>
                </form>

                <div id="status-message" class="mt-4" style="display: none;"></div>
            </div>
        </div>

        <div class="col-md-8">
            <div class="card p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold m-0 text-secondary">⏰ Continuous Late Comers Tracker</h5>
                    <span class="badge bg-danger rounded-pill px-3 py-2 fw-semibold">Live Tracking</span>
                </div>
                
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Student Name</th>
                                <th>Branch</th>
                                <th>Sec</th>
                                <th>Phone</th>
                                <th class="text-center">Late Days</th>
                                <th class="text-center">Action Status</th>
                                <th>Last Date</th>
                                <th>Last Time (IST)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for row in late_comers %}
                            <tr>
                                <td><strong>{{ row['student_id'] }}</strong></td>
                                <td>{{ row['student_name'] }}</td>
                                <td><span class="badge bg-light text-dark">{{ row['branch'] if row['branch'] and row['branch'] != 'nan' else '-' }}</span></td>
                                <td><span class="badge bg-light text-dark">{{ row['section'] if row['section'] and row['section'] != 'nan' else '-' }}</span></td>
                                <td class="text-muted small">{{ row['student_phone'] if row['student_phone'] and row['student_phone'] != 'nan' else '-' }}</td>
                                <td class="text-center fw-bold text-danger">
                                    <span class="bg-danger-subtle px-2 py-1 rounded">{{ row['late_days'] }} Days</span>
                                </td>
                                <td class="text-center">
                                    {% if row['late_days'] >= 3 %}
                                        <span class="badge badge-danger p-2 fw-bold">🔴 Suspension Call</span>
                                    {% elif row['late_days'] == 2 %}
                                        <span class="badge badge-warning p-2 fw-bold text-dark">⚠️ 2nd Warning</span>
                                    {% else %}
                                        <span class="badge badge-warning p-2 fw-semibold text-dark">1st Warning</span>
                                    {% endif %}
                                </td>
                                <td class="small">{{ row['last_date'].strftime('%d-%m-%Y') if row['last_date'] else '-' }}</td>
                                <td class="text-primary small fw-semibold">{{ row['last_time'].strftime('%I:%M %p') if row['last_time'] else '-' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    $('#attendance-form').on('submit', function() {
        let studentId = $('#student_id').val();
        $('#student_id').val(''); 
        
        $.post('/log_late', { student_id: studentId }, function(data) {
            let msgBox = $('#status-message');
            let actionText = data.late_count >= 3 ? '⚠️ CRITICAL ACTION: HOD Suspension Call issued.' : '1st Warning issued';
            if(data.late_count == 2) actionText = '⚠️ 2nd Warning issued';

            msgBox.html(`
                <div class="alert alert-success p-3 rounded-3 border-0 shadow-sm">
                    <h6 class="fw-bold text-success mb-2">✅ Entry logged! ${actionText}</h6>
                    <div class="small text-dark">
                        <strong>Name:</strong> ${data.student_name}<br>
                        <strong>Branch:</strong> ${data.branch}<br>
                        <strong>Section:</strong> ${data.section}<br>
                        <strong>Phone:</strong> ${data.phone}
                    </div>
                </div>
            `).fadeIn();
            
            setTimeout(function() { window.location.reload(); }, 2500);
        }).fail(function(err) {
            let errorMsg = err.responseJSON ? err.responseJSON.message : "Network transaction validation failed.";
            $('#status-message').html(`
                <div class="alert alert-danger p-3 border-0 rounded-3 small fw-semibold">
                    ❌ ${errorMsg}
                </div>
            `).fadeIn();
        });
    });
</script>

</body>
</html>
"""

# --------------------------------------------------------------------------------------
# CORE APP ROUTE CONTROLLERS
# --------------------------------------------------------------------------------------

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 🎯 Changed 's.phone' to 's.student_phone' to match your schema precisely
    cursor.execute('''
        SELECT 
            s.student_id, 
            s.student_name, 
            s.branch, 
            s.section, 
            s.student_phone,
            COUNT(le.id) as late_days,
            MAX(le.date) as last_date,
            MAX(le.time) as last_time
        FROM late_entries le
        JOIN students s ON le.student_id = s.student_id
        GROUP BY s.student_id, s.student_name, s.branch, s.section, s.student_phone
        ORDER BY last_date DESC, last_time DESC;
    ''')
    
    late_comers = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, late_comers=late_comers)



@app.route('/log_late', methods=['POST'])
def log_late():
    student_id = request.form.get('student_id', '').strip().upper()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT student_name, branch, section, student_phone FROM students WHERE student_id = %s;', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        cursor.close()
        conn.close()
        return jsonify({"status": "error", "message": f"Student ID '{student_id}' not recognized in DIET Database."}), 404

    today = datetime.date.today()
    now_time = datetime.datetime.now().time()
    cursor.execute('INSERT INTO late_entries (student_id, date, time) VALUES (%s, %s, %s);', (student_id, today, now_time))
    
    cursor.execute('SELECT COUNT(*) FROM late_entries WHERE student_id = %s;', (student_id,))
    late_count = cursor.fetchone()['count']
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        "status": "success",
        "student_id": student_id,
        "student_name": student['student_name'],
        "branch": student['branch'] if student['branch'] and student['branch'] != 'nan' else "N/A",
        "section": student['section'] if student['section'] and student['section'] != 'nan' else "N/A",
        "phone": student['student_phone'] if student['student_phone'] and student['student_phone'] != 'nan' else "N/A",
        "late_count": late_count
    })



# ... right below your @app.route('/log_late') function block ...

@app.route('/download_csv')
def download_csv():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            s.student_id, 
            s.student_name, 
            s.branch, 
            s.section, 
            s.student_phone,
            COUNT(le.id) as late_days
        FROM late_entries le
        JOIN students s ON le.student_id = s.student_id
        GROUP BY s.student_id, s.student_name, s.branch, s.section, s.student_phone
        ORDER BY late_days DESC;
    ''')
    
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    
    csv_data = "Student ID,Student Name,Branch,Section,Phone,Late Days\n"
    for row in records:
        csv_data += f"{row['student_id']},{row['student_name']},{row['branch']},{row['section']},{row['student_phone']},{row['late_days']}\n"
        
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=late_comers_report.csv"}
    )

# 🌟 KEEP THIS AS THE ABSOLUTE LAST TWO LINES OF YOUR FILE:
if __name__ == '__main__':
    app.run(debug=True)








