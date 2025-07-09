import cv2
import pandas as pd
from ultralytics import YOLO
import json
from datetime import datetime

def box_area(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)

def intersection_area(box, zone):
    bx1, by1, bx2, by2 = box
    zx1, zy1, zx2, zy2 = zone
    ix1 = max(bx1, zx1)
    iy1 = max(by1, zy1)
    ix2 = min(bx2, zx2)
    iy2 = min(by2, zy2)
    return max(0, ix2 - ix1) * max(0, iy2 - iy1)

def is_box_in_zone(box, zone, threshold=0.9):
    area = box_area(box)
    inter = intersection_area(box, zone)
    return area > 0 and (inter / area) >= threshold

class ComponentTracker:
    def __init__(self, config_path):
        self.load_config(config_path)
        self.components = {}
        self.boxes = {}
        self.zone_boxes = {tuple(tuple(coord) for coord in zone): None for zone in self.worker_zones}
        self.boxes_df = pd.DataFrame(columns=['box_id', 'first_detected', 'zone_id', 'zone_entry_time'])
        self.components_df = pd.DataFrame(columns=['component_id', 'box_id', 'first_detected', 'assignment_method'])
        self.processed_components = set()
        self.processed_boxes = set()

    def load_config(self, config_path):
        with open(config_path) as f:
            config = json.load(f)
        self.worker_zones = [tuple(map(tuple, zone)) for zone in config["worker_zones"]]
        self.middle_line = [tuple(point) for point in config["middle_line"]]

    def update_boxes(self, box_id, box_coords, centroid, timestamp):
        if box_id not in self.boxes:
            self.boxes[box_id] = {
                'first_detected': timestamp,
                'last_seen': timestamp,
                'centroid': centroid,
                'coords': box_coords,
                'side': self.get_side(centroid),
                'zone_entry_time': None,
                'zone_id': None
            }
            if box_id not in self.processed_boxes:
                self.boxes_df = pd.concat([self.boxes_df, pd.DataFrame([{
                    'box_id': box_id,
                    'first_detected': timestamp,
                    'zone_id': None,
                    'zone_entry_time': None
                }])], ignore_index=True)
                self.processed_boxes.add(box_id)
        else:
            self.boxes[box_id].update({
                'last_seen': timestamp,
                'centroid': centroid,
                'coords': box_coords,
                'side': self.get_side(centroid)
            })

    def update_box_zone(self, box_id, zone_idx, entry_time):
        self.boxes[box_id]['zone_id'] = zone_idx
        self.boxes[box_id]['zone_entry_time'] = entry_time
        mask = self.boxes_df['box_id'] == box_id
        self.boxes_df.loc[mask, ['zone_id', 'zone_entry_time']] = [zone_idx, entry_time]

    def get_side(self, point):
        (x1, y1), (x2, y2) = self.middle_line
        return (x2 - x1) * (point[1] - y1) - (y2 - y1) * (point[0] - x1) > 0

    def assign_component(self, c_id, entry_time, centroid):
        if c_id in self.processed_components:
            return

        assigned_box = None
        method = None

        for zone_idx, zone in enumerate(self.worker_zones):
            (x1, y1), (x2, y2) = zone
            zone_coords = (x1, y1, x2, y2)
            for box_id, box in self.boxes.items():
                if is_box_in_zone(box['coords'], zone_coords):
                    if x1 <= centroid[0] <= x2 and y1 <= centroid[1] <= y2:
                        assigned_box = box_id
                        method = 'zone'
                        break
            if method == 'zone':
                break

        if assigned_box is None:
            component_side = self.get_side(centroid)
            for zone_idx, zone in enumerate(self.worker_zones):
                zone_centroid = ((zone[0][0] + zone[1][0]) // 2, (zone[0][1] + zone[1][1]) // 2)
                if self.get_side(zone_centroid) == component_side:
                    zone_coords = (zone[0][0], zone[0][1], zone[1][0], zone[1][1])
                    for box_id, box in self.boxes.items():
                        if is_box_in_zone(box['coords'], zone_coords):
                            assigned_box = box_id
                            break
                    if not assigned_box:
                        for box_id, box in self.boxes.items():
                            if box['zone_id'] == zone_idx:
                                assigned_box = box_id
                    method = 'middle_line'
                    break

        self.components_df = pd.concat([self.components_df, pd.DataFrame([{
            'component_id': c_id,
            'box_id': assigned_box,
            'first_detected': entry_time,
            'assignment_method': method
        }])], ignore_index=True)
        self.processed_components.add(c_id)

    def save_to_csv(self):
        self.boxes_df.drop_duplicates(subset='box_id', keep='first', inplace=True)
        self.components_df.drop_duplicates(subset='component_id', keep='first', inplace=True)
        self.boxes_df.to_csv('boxes.csv', index=False)
        self.components_df.to_csv('main_components.csv', index=False)

def draw_zones_and_save_image(video_path, config_path):
    with open(config_path) as f:
        config = json.load(f)

    worker_zones = [tuple(map(tuple, zone)) for zone in config["worker_zones"]]
    middle_line = [tuple(point) for point in config["middle_line"]]

    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if ret:
        for (x1, y1), (x2, y2) in worker_zones:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        (x1, y1), (x2, y2) = middle_line
        cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.imwrite("first_frame_with_zones.jpg", frame)

def main():
    config_path = "second-zone-setup.json"
    video_path = "videos/second_run_right 1.mp4"
    draw_zones_and_save_image(video_path, config_path)

    tracker = ComponentTracker(config_path)
    model = YOLO("run/train5/weights/best.pt")

    # Setup video reader
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('output_with_annotations.mp4', fourcc, fps, (width, height))

    # Frame index to sync reading with tracking
    frame_idx = 0
    cap = cv2.VideoCapture(video_path)

    for result in model.track(source=video_path, stream=True, tracker="botsort.yaml"):
        ret, frame = cap.read()
        if not ret:
            break

        frame_time = datetime.now()
        if result.boxes.id is None:
            out.write(frame)
            continue

        for box in result.boxes:
            cls = int(box.cls[0].item())
            obj_id = int(box.id[0].item())
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            centroid = ((xyxy[0] + xyxy[2]) // 2, (xyxy[1] + xyxy[3]) // 2)
            box_coords = (xyxy[0], xyxy[1], xyxy[2], xyxy[3])

            label = f"{'Box' if cls==0 else 'Component'} {obj_id}"
            color = (255, 0, 0) if cls == 0 else (0, 255, 255)
            cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)
            cv2.putText(frame, label, (xyxy[0], xyxy[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if cls == 0:
                tracker.update_boxes(obj_id, box_coords, centroid, frame_time)
                for zone_idx, zone in enumerate(tracker.worker_zones):
                    zone_coords = (zone[0][0], zone[0][1], zone[1][0], zone[1][1])
                    if is_box_in_zone(box_coords, zone_coords):
                        if tracker.zone_boxes[zone] != obj_id:
                            tracker.update_box_zone(obj_id, zone_idx, frame_time)
                        tracker.zone_boxes[zone] = obj_id
            elif cls == 1:
                tracker.assign_component(obj_id, frame_time, centroid)

        # Draw zones and middle line for context
        for (x1, y1), (x2, y2) in tracker.worker_zones:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
        (x1, y1), (x2, y2) = tracker.middle_line
        cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 1)

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()
    tracker.save_to_csv()

if __name__ == "__main__":
    main()
