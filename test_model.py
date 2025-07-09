from ultralytics import YOLO
import cv2

model = YOLO("runs/detect/train5/weights/best.pt")

results = model.track(
    source="second_run_right.mp4",
    show=False,
    stream=True,
    tracker="botsort.yaml",
    conf=0.5
)

# Load original video for reading frames
cap = cv2.VideoCapture("second_run_right.mp4")
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

# Create output video writer
out = cv2.VideoWriter("output_tracked.mp4", cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))

frame_id = 0

for result in results:
    success, frame = cap.read()
    if not success:
        break

    if result.boxes is not None:
        for box in result.boxes:
            cls = int(box.cls[0].item())
            id = int(box.id[0].item()) if box.id is not None else -1
            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = xyxy

            color = (0, 0, 255) if cls == 0 else (0, 255, 0)  # Red for box, Green for component

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID:{id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    out.write(frame)
    frame_id += 1

cap.release()
out.release()
