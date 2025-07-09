from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # Load a pretrained YOLOv8n model

model.train(
    data="data.yaml", 
    epochs=50, 
    imgsz=640, 
    batch=8
)  