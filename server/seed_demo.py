"""Fills the database with 24 h of realistic readings (demo / screenshots).

  python seed_demo.py && python app.py
"""
import random
import sqlite3
from datetime import datetime, timedelta, timezone

from app import create_app

app = create_app()
conn = sqlite3.connect(app.config["DATABASE"])
conn.execute("DELETE FROM readings")
conn.execute("DELETE FROM events")
now = datetime.now(timezone.utc)
random.seed(4)
fmt = "%Y-%m-%dT%H:%M:%SZ"

profiles = {"bin-1": (12, 6.4, [9.0]), "bin-2": (30, 8.8, [6.5, 17.0])}   # start, %/h, emptied at (h)
for bin_id, (level, rate, emptied) in profiles.items():
    alert = False
    for i in range(24 * 6 + 1):                       # one reading every 10 min
        h = i / 6
        ts = (now - timedelta(hours=24) + timedelta(minutes=10 * i)).strftime(fmt)
        if any(abs(h - e) < 0.05 for e in emptied):
            level = random.uniform(0, 4)
            if alert:
                conn.execute("INSERT INTO events (bin_id, ts, kind, level, detail) VALUES (?,?,?,?,?)",
                             (bin_id, ts, "EMPTIED", int(level), "collecte effectuée"))
                alert = False
        else:
            level = min(100, level + rate / 6 * random.uniform(0.2, 1.8))
        if level >= 90 and not alert:
            alert = True
            conn.execute("INSERT INTO events (bin_id, ts, kind, level, detail) VALUES (?,?,?,?,?)",
                         (bin_id, ts, "FULL_ALERT", int(level), "WhatsApp: sent"))
        conn.execute("INSERT INTO readings (bin_id, ts, level, lid_open, rssi) VALUES (?,?,?,?,?)",
                     (bin_id, ts, int(level), 0, random.randint(-72, -55)))
    conn.execute("UPDATE bins SET alert_sent = ? WHERE id = ?", (int(alert), bin_id))
conn.commit()
print("demo data written to", app.config["DATABASE"])
