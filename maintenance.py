import csv
from config import MAINTENANCE_CSV


def get_last_maintenance(device, component):
    try:
        with open(MAINTENANCE_CSV, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["device"] == device and row["component"] == component:
                    return float(row["odometer"])
    except FileNotFoundError:
        pass
    return None


def update_maintenance(device, component, odometer):
    rows = []
    found = False
    try:
        with open(MAINTENANCE_CSV, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["device"] == device and row["component"] == component:
                    row["odometer"] = str(odometer)
                    found = True
                rows.append(row)
    except FileNotFoundError:
        pass
    if not found:
        rows.append({"device": device, "component": component, "odometer": str(odometer)})
    with open(MAINTENANCE_CSV, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["device", "component", "odometer"])
        writer.writeheader()
        writer.writerows(rows)
