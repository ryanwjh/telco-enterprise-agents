"""Generate synthetic seed CSV data for five_g_handset_upgrade."""
import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent

def generate_device_fleet_inventory():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "device_fleet_inventory.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def generate_network_coverage_5g():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "network_coverage_5g.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def generate_upgrade_incentive_campaigns():
    headers = ["id", "timestamp", "entity_id", "region", "metric_value", "status_flag"]
    rows = [
        ["REC-001", "2026-08-01 10:00:00", "ENT-101", "Metro-North", 125.50, "ACTIVE"],
        ["REC-002", "2026-08-02 11:30:00", "ENT-102", "Metro-South", 88.20, "COMPLETED"],
        ["REC-003", "2026-08-03 14:15:00", "ENT-103", "West-Region", 210.00, "OPTIMAL"],
        ["REC-004", "2026-08-04 09:45:00", "ENT-104", "East-Region", 94.75, "ACTIVE"],
        ["REC-005", "2026-08-05 16:20:00", "ENT-105", "Central-Hub", 165.30, "VERIFIED"],
    ]
    with open(DATA_DIR / "upgrade_incentive_campaigns.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def main():
    generate_device_fleet_inventory()
    generate_network_coverage_5g()
    generate_upgrade_incentive_campaigns()
    print("five_g_handset_upgrade seed data generated.")

if __name__ == "__main__":
    main()
