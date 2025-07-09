import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import json
import os
import cv2

# === Globals ===
zones = []
middle_line = []
start_x = start_y = None
drawing = False
temp_shape = None
tool_buttons = {}

# === Extract First Frame from Video ===
VIDEO_PATH = "videos/_2025-05-28_15_29_37_583 (online-video-cutter.com).mp4"
cap = cv2.VideoCapture(VIDEO_PATH)
ret, frame = cap.read()
cap.release()

if not ret or frame is None:
    raise ValueError("❌ Could not read frame from video.")

# Convert OpenCV BGR to RGB for PIL
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
image = Image.fromarray(frame_rgb)
width, height = image.size

# === Tkinter Setup ===
root = tk.Tk()
root.title("Worker Zone Config")
mode = tk.StringVar(value="Worker Zone")

canvas = tk.Canvas(root, width=width, height=height, bg="white")
canvas.grid(row=0, column=1)
tk.Frame(root, width=160).grid(row=0, column=0)  # Sidebar spacer

# === Drawing Callbacks ===
def on_mouse_down(event):
    global start_x, start_y, drawing, temp_shape
    start_x, start_y = event.x, event.y
    drawing = True

def on_mouse_move(event):
    global temp_shape
    if not drawing:
        return
    canvas.delete(temp_shape)

    if mode.get() == "Worker Zone":
        temp_shape = canvas.create_rectangle(start_x, start_y, event.x, event.y, outline="red", width=2)
    elif mode.get() == "Middle Line":
        temp_shape = canvas.create_line(start_x, start_y, event.x, event.y, fill="green", width=4)

def on_mouse_up(event):
    global drawing, temp_shape
    drawing = False
    canvas.delete(temp_shape)

    if mode.get() == "Worker Zone":
        zones.append(((start_x, start_y), (event.x, event.y)))
    elif mode.get() == "Middle Line":
        canvas.delete("middle_line")
        middle_line.clear()
        middle_line.extend([(start_x, start_y), (event.x, event.y)])
    elif mode.get() == "Eraser":
        x, y = event.x, event.y
        for i, ((x1, y1), (x2, y2)) in enumerate(zones):
            if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
                zones.pop(i)
                redraw()
                return
        if len(middle_line) == 2:
            mx1, my1 = middle_line[0]
            mx2, my2 = middle_line[1]
            dist = abs((my2 - my1) * x - (mx2 - mx1) * y + mx2 * my1 - my2 * mx1) / (((my2 - my1) ** 2 + (mx2 - mx1) ** 2) ** 0.5)
            if dist < 10:
                middle_line.clear()
                redraw()
                return
    redraw()

# === Redraw everything ===
def redraw():
    canvas.delete("all")
    canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
    for (x1, y1), (x2, y2) in zones:
        canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)
    if len(middle_line) == 2:
        canvas.create_line(middle_line[0], middle_line[1], fill="green", width=4, tags="middle_line")
    update_button_styles()

# === Buttons ===
def select_mode(new_mode):
    mode.set(new_mode)
    update_button_styles()

def update_button_styles():
    for value, btn in tool_buttons.items():
        btn.configure(bg="#dddddd" if value == mode.get() else "#ffffff")

def save_config():
    # Save JSON
    config = {
        "worker_zones": zones,
        "middle_line": middle_line
    }
    json_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
    if json_path:
        with open(json_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"✅ Zones saved to {json_path}")

        # Save annotated image
        annotated = frame.copy()
        for (x1, y1), (x2, y2) in zones:
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if len(middle_line) == 2:
            (x1, y1), (x2, y2) = middle_line
            cv2.line(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)

        out_path = os.path.splitext(json_path)[0] + "_zones.jpg"
        cv2.imwrite(out_path, annotated)
        print(f"🖼️ Annotated image saved to {out_path}")

# === Sidebar UI ===
sidebar = tk.Frame(root, bg="white")
sidebar.place(x=0, y=0, width=160, height=height)

buttons = [
    ("🟥 Worker Zone", "Worker Zone"),
    ("🟩 Middle Line", "Middle Line"),
    ("🧽 Eraser", "Eraser"),
    ("💾 Save", "Save"),
    ("❌ Exit", "Exit")
]

for i, (label, value) in enumerate(buttons):
    def handler(v=value):
        if v == "Save":
            save_config()
        elif v == "Exit":
            root.destroy()
        else:
            select_mode(v)
        redraw()
    b = tk.Button(sidebar, text=label, anchor="w", padx=10, relief=tk.FLAT, command=handler)
    b.place(x=0, y=i * 50, width=160, height=50)
    tool_buttons[value] = b

# === Load Image into Canvas ===
imgtk = ImageTk.PhotoImage(image)
canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)

canvas.bind("<Button-1>", on_mouse_down)
canvas.bind("<B1-Motion>", on_mouse_move)
canvas.bind("<ButtonRelease-1>", on_mouse_up)

update_button_styles()
root.mainloop()
