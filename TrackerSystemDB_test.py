import cv2
import pandas as pd
from ultralytics import YOLO
import json
from datetime import datetime
import pyodbc                                       # ← NEW
print(pyodbc.drivers())

# ────────────────────────────────────────────────
# SQL‑SERVER CONNECTION SETTINGS ─ edit if needed
# ────────────────────────────────────────────────
DB_CONFIG = {
    "driver": "ODBC Driver 17 for SQL Server",      # or 17, 11… (check ODBC Data Sources)
    "server": "CUIDADO\SQLEXPRESS",                          # "." or "localhost\\SQLEXPRESS" also work
    "database": "Logical DB",
    "trusted_connection": "yes",                   
}
# ────────────────────────────────────────────────


def box_area(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def intersection_area(box, zone):
    bx1, by1, bx2, by2 = box
    zx1, zy1, zx2, zy2 = zone
    ix1, iy1 = max(bx1, zx1), max(by1, zy1)
    ix2, iy2 = min(bx2, zx2), min(by2, zy2)
    return max(0, ix2 - ix1) * max(0, iy2 - iy1)


def is_box_in_zone(box, zone, threshold=0.9):
    area = box_area(box)
    inter = intersection_area(box, zone)
    return area and (inter / area) >= threshold


import pyodbc
import pandas as pd
import json

class ComponentTracker:
    def __init__(self, config_path):
        self.load_config(config_path)

        # Now that self.worker_zones exists, we can use it
        self.zone_boxes = {tuple(tuple(c) for c in z): None for z in self.worker_zones}
        
        self.components = {}
        self.boxes = {}

        self.boxes_df = pd.DataFrame(
            columns=["box_id", "first_detected", "zone_id", "zone_entry_time"]
        )
        self.components_df = pd.DataFrame(
            columns=["component_id", "box_id", "first_detected", "assignment_method"]
        )
        self.processed_components, self.processed_boxes = set(), set()

        # Connect to the SQL Server database
        self.conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=CUIDADO\SQLEXPRESS;"
            "DATABASE=Logical DB;"
            "Trusted_Connection=yes;"
        )
        self.cursor = self.conn.cursor()

    def load_config(self, config_path):
        with open(config_path) as f:
            config = json.load(f)
        self.worker_zones = [tuple(map(tuple, zone)) for zone in config["worker_zones"]]
        self.middle_line = [tuple(point) for point in config["middle_line"]]

    def save_to_db(self):
        try:
            # Build connection string from DB_CONFIG dictionary
            conn_str = (
                f"DRIVER={DB_CONFIG['driver']};"
                f"SERVER={DB_CONFIG['server']};"
                f"DATABASE={DB_CONFIG['database']};"
            )

            print("Connecting using connection string:")
            print(conn_str)

            conn = pyodbc.connect(conn_str, autocommit=False)
            cur = conn.cursor()

            # Ensure one row per primary key
            self.boxes_df.drop_duplicates(subset="box_id", keep="first", inplace=True)
            self.components_df.drop_duplicates(subset="component_id", keep="first", inplace=True)

            # Insert / upsert Boxes
            for _, r in self.boxes_df.iterrows():
                cur.execute(
                    """
                    MERGE dbo.Boxes AS tgt
                    USING (SELECT ? AS UniqueID, ? AS BoxID) AS src
                    ON tgt.UniqueID = src.UniqueID
                    WHEN MATCHED THEN
                        UPDATE SET first_detected=?, zone_id=?, TimeAtLocation1=?, Barcodo=?
                    WHEN NOT MATCHED THEN
                        INSERT (UniqueID, BoxID, first_detected, zone_id, TimeAtLocation1, Barcodo)
                        VALUES (src.UniqueID, src.BoxID, ?, ?, ?, ?);
                    """,
                    r.box_id,
                    r.box_id,
                    r.first_detected,
                    r.zone_id,
                    r.zone_entry_time,
                    None,
                    r.first_detected,
                    r.zone_id,
                    r.zone_entry_time,
                    None,
                )

            # Insert / upsert Items
            for _, r in self.components_df.iterrows():
                cur.execute(
                    """
                    MERGE dbo.Items AS tgt
                    USING (SELECT ? AS UniqueID) AS src
                    ON tgt.UniqueID = src.UniqueID
                    WHEN MATCHED THEN
                        UPDATE SET BoxID=?, first_detected=?, assignment_method=?
                    WHEN NOT MATCHED THEN
                        INSERT (UniqueID, BoxID, first_detected, assignment_method)
                        VALUES (src.UniqueID, ?, ?, ?);
                    """,
                    r.component_id,
                    r.box_id,
                    r.first_detected,
                    r.assignment_method,
                    r.box_id,
                    r.first_detected,
                    r.assignment_method,
                )

            conn.commit()

        except pyodbc.Error as e:
            print("Database connection error:", e)

        finally:
            try:
                cur.close()
                conn.close()
            except:
                pass



def draw_zones_and_save_image(video_path, config_path):
    # (unchanged helper)
    pass


def main():
    config_path = "zone_setup.json"
    video_path = "videos/_2025-05-28_15_29_37_583 (online-video-cutter.com).mp4"
    draw_zones_and_save_image(video_path, config_path)

    tracker = ComponentTracker(config_path)
    model = YOLO("run/train5/weights/best.pt")

    cap = cv2.VideoCapture(video_path)
    width, height = int(cap.get(3)), int(cap.get(4))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    out = cv2.VideoWriter("output_with_annotations_DB.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    cap = cv2.VideoCapture(video_path)

    for result in model.track(source=video_path, stream=True, tracker="botsort.yaml"):
        ret, frame = cap.read()
        if not ret:
            break

        frame_time = datetime.now()
        if result.boxes.id is None:
            out.write(frame)
            continue

        # (tracking + drawing logic identical to your original snippet)
        # …

        out.write(frame)

    cap.release()
    out.release()
    tracker.save_to_db()            # ← NOW WRITES TO SQL SERVER


if __name__ == "__main__":
    main()
