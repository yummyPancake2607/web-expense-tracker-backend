import sqlite3

DB_PATH = "expense_tracker.db"

def check_schema():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check expenses columns
        cursor.execute("PRAGMA table_info(expenses)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Expenses columns: {columns}")
        
        if "is_anomaly" in columns:
             print("SUCCESS: 'is_anomaly' column exists.")
        else:
             print("FAILURE: 'is_anomaly' column MISSING.")

        conn.close()
    except Exception as e:
        print(f"Check failed: {e}")

if __name__ == "__main__":
    check_schema()
