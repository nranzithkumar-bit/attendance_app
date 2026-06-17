import pandas as pd
import psycopg2

# 1. Read the Excel file and clean any blank cells
print("Reading students.xlsx...")
df = pd.read_excel("students.xlsx").fillna("")

# Rename Excel columns to match your exact Supabase database names
df = df.rename(columns={"section": "sec", "Phone": "phone"})

# 2. ADD YOUR SUPABASE CONNECTION STRING HERE
DATABASE_URL = "postgresql://postgres:Diet2025#DIET@db.ujjoynqjmzuurefkapbu.supabase.co:5432/postgres"

try:
    print("Connecting to Supabase Cloud...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # 3. Loop through every single row and insert/update the cloud database
    for index, row in df.iterrows():
        cursor.execute(
            """
            INSERT INTO students (student_id, student_name, branch, sec, phone)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (student_id) 
            DO UPDATE SET 
                student_name = EXCLUDED.student_name,
                branch = EXCLUDED.branch,
                sec = EXCLUDED.sec,
                phone = EXCLUDED.phone;
            """,
            (str(row['student_id']), str(row['student_name']), str(row['branch']), str(row['sec']), str(row['phone']))
        )

    conn.commit()
    print(f"✅ SUCCESS: All {len(df)} students safely synced to Supabase!")

except Exception as e:
    print(f"❌ DATABASE ERROR: {e}")
finally:
    if 'conn' in locals() and conn:
        cursor.close()
        conn.close()