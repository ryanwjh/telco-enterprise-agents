"""Generate synthetic seed CSV data for tourist_welcome_roaming."""
import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent

def generate_inbound_roamer_events():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "inbound_roamer_events.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def generate_tourist_pass_catalog():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "tourist_pass_catalog.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def generate_multilingual_welcome_conversions():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "multilingual_welcome_conversions.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def main():
    generate_inbound_roamer_events()
    generate_tourist_pass_catalog()
    generate_multilingual_welcome_conversions()
    print("tourist_welcome_roaming seed data generated.")

if __name__ == "__main__":
    main()
