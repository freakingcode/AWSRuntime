import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
print(f"Initializing database at: {BASE_DIR}")
db_path = BASE_DIR / "inventory.db"
schema_path = BASE_DIR / "schema.sql"

with sqlite3.connect(db_path) as conn:
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

print("Database initialized successfully.")

