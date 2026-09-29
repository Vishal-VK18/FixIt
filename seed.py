"""Insert realistic sample maintenance tickets for local development."""

from datetime import datetime, timedelta

import db


SAMPLE_TICKETS = [
    ("Ceiling fan not working", "Electrical", "HIGH", "Electrical Maintenance", "Inspect wiring and replace the fan motor", "C", "101", 0),
    ("Flickering classroom lights", "Electrical", "MEDIUM", "Electrical Maintenance", "Check ballast and wiring", "C", "102", 2),
    ("Exposed electrical wire", "Electrical", "CRITICAL", "Electrical Maintenance", "Isolate power and repair wiring", "C", "103", 1),
    ("Power outlet sparking", "Electrical", "CRITICAL", "Electrical Maintenance", "Replace the damaged outlet", "C", "104", 5),
    ("Corridor lights not working", "Electrical", "MEDIUM", "Electrical Maintenance", "Replace bulbs and inspect circuit", "C", "105", 12),
    ("Electrical panel making noise", "Electrical", "HIGH", "Electrical Maintenance", "Inspect breaker panel", "C", "106", 22),
    ("Water leakage near washroom", "Plumbing", "HIGH", "Plumbing", "Repair leaking pipe joint", "A", "201", 1),
    ("Broken classroom chair", "Furniture", "LOW", "Carpentry", "Replace chair leg", "A", "202", 4),
    ("Damaged corridor tile", "Civil", "MEDIUM", "Civil Works", "Replace loose tile", "B", "110", 8),
    ("Wi-Fi access point not working", "IT/Network", "HIGH", "IT Support", "Check access point power and network", "B", "111", 0),
    ("Blocked drainage", "Sanitation", "HIGH", "Sanitation", "Clear drain and disinfect area", "D", "301", 3),
    ("Broken window latch", "Other", "LOW", "General Maintenance", "Replace latch", "D", "302", 15),
    ("Water pressure low", "Plumbing", "MEDIUM", "Plumbing", "Inspect supply valve", "E", "401", 6),
    ("Projector power socket loose", "Electrical", "MEDIUM", "Electrical Maintenance", "Secure socket and test", "A", "203", 18),
    ("Desk drawer jammed", "Furniture", "LOW", "Carpentry", "Repair drawer runners", "E", "402", 10),
    ("Cracked stairwell plaster", "Civil", "LOW", "Civil Works", "Patch and repaint plaster", "D", "303", 28),
    ("Printer disconnected from network", "IT/Network", "MEDIUM", "IT Support", "Restore network connection", "A", "204", 36),
    ("Washroom tap dripping", "Plumbing", "LOW", "Plumbing", "Replace tap washer", "B", "112", 45),
    ("Overflowing waste bin", "Sanitation", "LOW", "Sanitation", "Empty bin and adjust collection schedule", "E", "403", 55),
    ("Loose ceiling panel", "Civil", "MEDIUM", "Civil Works", "Secure ceiling panel", "C", "107", 70),
]
SAMPLE_STATUSES = ("Reported", "Assigned", "Fixed", "Reported", "Assigned")


def seed() -> None:
    db.init_db()
    if db.get_tickets():
        print("Database already contains tickets; no sample data inserted.")
        return

    now = datetime.now()
    records = []
    for index, (issue, category, priority, department, fix, block, room, days_ago) in enumerate(SAMPLE_TICKETS):
        created = (now - timedelta(days=days_ago, hours=index * 2)).isoformat(timespec="seconds", sep=" ")
        updated = (now - timedelta(days=days_ago, hours=index)).isoformat(timespec="seconds", sep=" ")
        records.append((issue, category, priority, department, fix, block, room, SAMPLE_STATUSES[index % len(SAMPLE_STATUSES)], created, updated))
    db.insert_sample_tickets(records)

    block_c_electrical = sum(
        1 for item in SAMPLE_TICKETS if item[5] == "C" and item[1] == "Electrical" and item[7] <= 30
    )
    print("Database initialized.")
    print(f"Inserted {len(SAMPLE_TICKETS)} sample tickets.")
    print(f"Block C Electrical issues: {block_c_electrical}")
    print("Predictive maintenance threshold: 4")
    print("Seed complete.")


if __name__ == "__main__":
    seed()
