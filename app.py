import os
import datetime
import pytz
import pandas as pd  
from flask import Flask, request, render_template_string, jsonify, Response
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not found")

def get_db_connection():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

def init_cloud_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id VARCHAR(50) PRIMARY KEY,
            student_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
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
    print("Database initialized successfully!")


def seed_students_from_excel():
    excel_file = "students.xlsx"
    if not os.path.exists(excel_file):
        return
    try:
        df = pd.read_excel(excel_file)
        conn = get_db_connection()
        cursor = conn.cursor()
        inserted_count = 0
        for index, row in df.iterrows():
            student_id = str(row.get('student_id', '')).strip().upper()
            student_name = str(row.get('student_name', '')).strip()
            phone = str(row.get('phone', '')).strip()
            branch = str(row.get('branch', '')).strip()
            section = str(row.get('section', '')).strip()
            if not student_id or student_id == 'NAN':
                continue
            cursor.execute('''
                INSERT INTO students (student_id, student_name, phone, branch, section) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (student_id)
                DO UPDATE SET student_name = EXCLUDED.student_name, phone = EXCLUDED.phone, branch = EXCLUDED.branch, section = EXCLUDED.section;
            ''', (student_id, student_name, phone, branch, section))
            inserted_count += 1
        conn.commit()
    except Exception as e:
        print(f"Excel error: {str(e)}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()


init_cloud_db()
seed_students_from_excel()


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
        .btn-processing { opacity: 0.8; cursor: not-allowed; }
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
            <a href="/download_csv" class="btn btn-success fw-semibold btn-sm px-3 d-flex align-items-center gap-1">📥 Download Report (CSV)</a>
            <button class="btn btn-light fw-semibold btn-sm px-3 text-primary" id="refresh-btn" onclick="refreshPage()">🔄 Refresh Page</button>
        </div>
    </div>
</nav>

<div class="container-fluid px-4">
    <div class="row g-4">
        <div class="col-md-4">
            <div class="card p-4">
                <h5 class="fw-bold mb-3 text-secondary">📋 Log Late Entry</h5>
                <form id="attendance-form" onsubmit="return false;">
                    <label class="form-label text-muted fw-semibold small">TYPE STUDENT ID</label>
                    <input type="text" id="student_id" name="student_id" class="form-control form-control-lg border-primary mb-3" placeholder="Enter Roll Number / ID..." autofocus required autocomplete="off">
                    <button type="submit" id="submit-btn" class="btn btn-primary btn-lg w-100 fw-bold">Log Entry & Verify</button>
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
                                <th>Last Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for row in late_comers %}
                            <tr>
                                <td><strong>{{ row['student_id'] }}</strong></td>
                                <td>{{ row['student_name'] }}</td>
                                <td><span class="badge bg-light text-dark">{{ row['branch'] if row['branch'] and row['branch'] != 'nan' else '-' }}</span></td>
                                <td><span class="badge bg-light text-dark">{{ row['section'] if row['section'] and row['section'] != 'nan' else '-' }}</span></td>
                                <td class="text-muted small">{{ row['phone'] if row['phone'] and row['phone'] != 'nan' else '-' }}</td>
                                <td class="text-center fw-bold text-danger">
                                    <span class="bg-danger-subtle px-2 py-1 rounded">{{ row['late_days'] }} Days</span>
                                </td>
                                <td class="text-center">
                                    {% if row['late_days'] >= 3 %}
                                        <span class="badge badge-danger p-2 fw-bold text-uppercase">💸 Pay Rs 100 Fine</span>
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
    // Bug 3 Fix: Refresh button
    function refreshPage() {
        $('#refresh-btn').text('🔄 Refreshing...').prop('disabled', true);
        window.location.href = window.location.href;
    }

    // Bug 1 Fix: Button Processing animation
    $('#attendance-form').on('submit', function() {
        let studentId = $('#student_id').val().trim();
        if(!studentId) return;

        // Show Processing on button
        let btn = $('#submit-btn');
        btn.text('⏳ Processing...').prop('disabled', true).addClass('btn-processing');

        $('#student_id').val(''); 
        
        $.post('/log_late', { student_id: studentId }, function(data) {
            let msgBox = $('#status-message');
            
            if (data.status === "warning") {
                msgBox.html(`
                    <div class="alert alert-warning p-3 rounded-3 border-0 shadow-sm fw-bold text-dark">
                        ⚠️ ${data.message}
                    </div>
                `).fadeIn();
            } else {
                let actionText = data.late_count >= 3 ? '💸 Fine condition met: Pay Rs 100 fine.' : '1st Warning logged';
                if(data.late_count == 2) actionText = '⚠️ 2nd Warning logged';

                msgBox.html(`
                    <div class="alert alert-success p-3 rounded-3 border-0 shadow-sm">
                        <h6 class="fw-bold text-success mb-2">✅ Entry logged! ${actionText}</h6>
                        <div class="small text-dark">
                            <strong>Name:</strong> ${data.student_name}<br>
                            <strong>Branch:</strong> ${data.branch}<br>
                            <strong>Section:</strong> ${data.section}
                        </div>
                    </div>
                `).fadeIn();
            }

            // Reset button after response
            btn.text('Log Entry & Verify').prop('disabled', false).removeClass('btn-processing');
            $('#student_id').focus();
            
            setTimeout(function() { window.location.reload(); }, 2500);

        }).fail(function(err) {
            let errorMsg = err.responseJSON ? err.responseJSON.message : "Validation transaction failed.";
            $('#status-message').html(`
                <div class="alert alert-danger p-3 border-0 rounded-3 small fw-semibold">
                    ❌ ${errorMsg}
                </div>
            `).fadeIn();

            // Reset button on error too
            btn.text('Log Entry & Verify').prop('disabled', false).removeClass('btn-processing');
            $('#student_id').focus();
        });
    });
</script>

</body>
</html>
"""

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()



    cursor.execute('''
        SELECT s.student_id, s.student_name, s.branch, s.section, s.phone,
               COUNT(le.id) as late_days,
               MAX(le.date) as last_date,
               MAX(le.time) as last_time,
               MAX((le.date::text || ' ' || le.time::text)::timestamp) as last_entry
        FROM late_entries le
        JOIN students s ON le.student_id = s.student_id
        GROUP BY s.student_id, s.student_name, s.branch, s.section, s.phone
        ORDER BY last_entry DESC;
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
    
    cursor.execute('SELECT student_name, branch, section, phone FROM students WHERE student_id = %s;', (student_id,))
    student = cursor.fetchone()
    
    if not student:
        cursor.close()
        conn.close()
        return jsonify({"status": "error", "message": f"ID '{student_id}' not recognized."}), 404

    # Bug 2 Fix: IST timezone
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(IST)
    now_time = now.time().replace(tzinfo=None)
    cutoff_time = datetime.time(9, 1, 0) # = 09:01:00 AM
    
    if now_time < cutoff_time:
        cursor.close()
        conn.close()
        return jsonify({
            "status": "warning", 
            "message": f"Student is ON TIME. Late logging starts from 09:01 AM. (Scanned at {now_time.strftime('%I:%M %p')})"
        })

    today = now.date()
    cursor.execute('SELECT id FROM late_entries WHERE student_id = %s AND date = %s;', (student_id, today))
    already_logged = cursor.fetchone()
    
    if already_logged:
        cursor.close()
        conn.close()
        return jsonify({"status": "warning", "message": "Already logged in for today!"})

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
        "late_count": late_count
    })

@app.route('/download_csv')
def download_csv():
    conn = get_db_connection()
    cursor = conn.cursor()


    cursor.execute('''
        SELECT s.student_id, s.student_name, s.branch, s.section, s.phone, COUNT(le.id) as late_days, MAX((le.date::text || ' ' || le.time::text)::timestamp) as last_entry
        FROM late_entries le
        JOIN students s ON le.student_id = s.student_id
        GROUP BY s.student_id, s.student_name, s.branch, s.section, s.phone
        ORDER BY last_entry DESC;
    ''')


    records = cursor.fetchall()
    cursor.close()
    conn.close()
    
    csv_data = "Student ID,Student Name,Branch,Section,Phone,Late Days,Action Status\n"
    for row in records:
        status = "Pay Rs 100 Fine" if row['late_days'] >= 3 else f"Warning {row['late_days']}"
        csv_data += f"{row['student_id']},{row['student_name']},{row['branch']},{row['section']},{row['phone']},{row['late_days']},{status}\n"
        
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=DIET_Late_Comers_Report.csv"}
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)