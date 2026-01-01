import sqlite3
import os

# Adjust filename if necessary. Assuming we run this from e:\InsightSpend\backend
DB_FILE = "expense_tracker.db"

def fix_db():
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found in {os.getcwd()}")
        return

    print(f"Connecting to {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # check existing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Current columns: {columns}")

    if "reminder_enabled" not in columns:
        print("Adding reminder_enabled...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN reminder_enabled BOOLEAN DEFAULT 0")
        except Exception as e:
            print(f"Error adding reminder_enabled: {e}")
    else:
        print("reminder_enabled already exists.")

    if "reminder_time" not in columns:
        print("Adding reminder_time...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN reminder_time VARCHAR DEFAULT '20:00'")
        except Exception as e:
            print(f"Error adding reminder_time: {e}")
    else:
        print("reminder_time already exists.")

    conn.commit()
    conn.close()
    print("Database Update Complete.")

if __name__ == "__main__":
    fix_db()
