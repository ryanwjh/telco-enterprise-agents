"""Generate synthetic seed CSV data for vip_high_arpu_concierge."""
import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent

def generate_platinum_subscriber_rosters():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "platinum_subscriber_rosters.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def generate_dedicated_concierge_tickets():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "dedicated_concierge_tickets.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def generate_sla_resolution_timelines():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "sla_resolution_timelines.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def main():
    generate_platinum_subscriber_rosters()
    generate_dedicated_concierge_tickets()
    generate_sla_resolution_timelines()
    print("vip_high_arpu_concierge seed data generated.")

if __name__ == "__main__":
    main()
