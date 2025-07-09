import os
import cv2
import json

print("Video exists:", os.path.exists("videos/second_run_right 1.mp4"))

with open("second-zone-setup.json") as f:
    config = json.load(f)

worker_zones = [tuple(map(tuple, zone)) for zone in config["worker_zones"]]
middle_line = [tuple(point) for point in config["middle_line"]]

cap = cv2.VideoCapture("videos/second_run_right 1.mp4")
ret, frame = cap.read()
cap.release()

print("Video frame read successful:", ret)
if ret and frame is not None:
    for (x1, y1), (x2, y2) in worker_zones:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    (x1, y1), (x2, y2) = middle_line
    cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

    success = cv2.imwrite("first_frame_with_zones.jpg", frame)
    print("Image save success:", success)
else:
    print("Failed to capture frame.")
