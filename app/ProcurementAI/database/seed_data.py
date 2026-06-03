import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
db_path = BASE_DIR / "inventory.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

products = [
    ("iPhone 15", "Mobile", "APL-IP15", 50, 10, 79999),
    ("Samsung TV", "Electronics", "SMS-TV01", 20, 5, 45000),
    ("MacBook Air", "Laptop", "APL-MBA", 15, 3, 120000),
]

cursor.executemany("""
INSERT INTO products
(name, category, sku, stock, reorder_level, price)
VALUES (?, ?, ?, ?, ?, ?)
""", products)

conn.commit()
conn.close()

print("Seed data inserted.")