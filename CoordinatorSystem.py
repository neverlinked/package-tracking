import pandas as pd

boxes = pd.read_csv("mock_data_boxes.csv", parse_dates=["first_detected"])
components = pd.read_csv("mock_data_components.csv", parse_dates=["first_detected"])
barcodes = pd.read_csv("mock_data_reader.csv", parse_dates=["time_of_detection"])

boxes = boxes.sort_values("first_detected").reset_index(drop=True)
components = components.sort_values("first_detected").reset_index(drop=True)
barcodes = barcodes.sort_values("time_of_detection").reset_index(drop=True)

if len(boxes) > len(barcodes):
    print(f"⚠️ More boxes ({len(boxes)}) than total barcodes ({len(barcodes)})!")

box_barcodes = barcodes.iloc[:len(boxes)].reset_index(drop=True)
component_barcodes = barcodes.iloc[len(boxes):len(boxes)+len(components)].reset_index(drop=True)

if len(components) > len(component_barcodes):
    print(f"⚠️ More components ({len(components)}) than available component barcodes ({len(component_barcodes)})!")

final_df = pd.DataFrame({
    "box_id": boxes["box_id"],
    "box_barcode": box_barcodes["barcode"],
    "component_id": components["component_id"].astype("Int64") if len(components) else pd.Series(dtype="Int64"),
    "component_barcode": component_barcodes["barcode"] if len(component_barcodes) else pd.Series(dtype="object")
})

def classify(row):
    if pd.isna(row["component_id"]): return "No component"
    if pd.isna(row["component_barcode"]): return "No component barcode"
    return "OK"

final_df["status"] = final_df.apply(classify, axis=1)

final_df.to_csv("final_merged_output.csv", index=False)
print("✅ Final CSV with status saved as 'final_merged_output.csv'")
