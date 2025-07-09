from ultralytics import YOLO
import cv2
import pyodbc
from datetime import datetime

# --- Connect to SQL Server ---
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER= database host;'
    'DATABASE= database name;' 
    'Trusted_Connection=yes;'
)
cursor = conn.cursor()

# --- Load YOLO model ---
model = YOLO("runs/detect/train5/weights/best.pt")

results = model.track(
    source="second_run_right.mp4",
    show=False,
    stream=True,
    tracker="botsort.yaml",
    conf=0.5
)

# --- Prepare video ---
cap = cv2.VideoCapture("second_run_right.mp4")
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

out = cv2.VideoWriter("output_tracked.mp4", cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))

frame_id = 0

for result in results:
    success, frame = cap.read()
    if not success:
        break

    if result.boxes is not None:
        for box in result.boxes:
            cls = int(box.cls[0].item())
            obj_id = int(box.id[0].item()) if box.id is not None else -1
            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = xyxy

            color = (0, 0, 255) if cls == 0 else (0, 255, 0)  # Red for box, Green for component
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID:{obj_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Current timestamp
            timestamp = datetime.now()

            # Insert into database
            if cls == 0:
                # It's a box
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM Boxes WHERE UniqueID = ?)
                    INSERT INTO Boxes (UniqueID, TimeAtLocation1)
                    VALUES (?, ?)
                """, obj_id, obj_id, timestamp)
            else:
                # It's a component
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM Items WHERE UniqueID = ?)
                    INSERT INTO Items (UniqueID, BoxID, TimeAtLocation2)
                    VALUES (?, ?, ?)
                """, obj_id, None, timestamp)  # Add logic for BoxID assignment if needed

    out.write(frame)
    frame_id += 1
    conn.commit()

cap.release()
out.release()
cursor.close()
conn.close()
