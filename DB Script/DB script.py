import pyodbc
from datetime import datetime

# Connect to your SQL Server
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=YOUR_SERVER_NAME;'
    'DATABASE=YOUR_DATABASE_NAME;'
    'UID=YOUR_USERNAME;'
    'PWD=YOUR_PASSWORD'
)
cursor = conn.cursor()

# Insert box record
def insert_box(unique_id, timestamp, barcode):
    try:
        cursor.execute(
            "INSERT INTO Boxes (UniqueID, TimeAtLocation1, Barcode) VALUES (?, ?, ?)",
            unique_id, timestamp, barcode
        )
        conn.commit()
    except pyodbc.IntegrityError:
        print(f"[!] Box {unique_id} already exists. Skipping.")

# Insert item record
def insert_item(unique_id, box_id, timestamp, barcode):
    try:
        cursor.execute(
            "INSERT INTO Items (UniqueID, BoxID, TimeAtLocation2, Barcode) VALUES (?, ?, ?, ?)",
            unique_id, box_id, timestamp, barcode
        )
        conn.commit()
    except pyodbc.IntegrityError:
        print(f"[!] Item {unique_id} already exists or BoxID {box_id} invalid.")

# Example usage (from your YOLO/Roboflow pipeline):
insert_box("box_001", datetime.now(), "BOX123456")
insert_item("item_001", "box_001", datetime.now(), "ITEM987654")
