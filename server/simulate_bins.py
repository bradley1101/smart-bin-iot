"""Sends fake telemetry for bin-1 and bin-2, to try the dashboard without hardware.

  python simulate_bins.py            (server on http://localhost:5000)
"""
import random
import time

import requests

URL = "http://localhost:5000/api/bins/{}/telemetry"
TOKEN = "change-me"
levels = {"bin-1": 35, "bin-2": 70}

while True:
    for bin_id in levels:
        if levels[bin_id] >= 100 or random.random() < 0.02:
            levels[bin_id] = random.randint(0, 8)            # collected
        else:
            levels[bin_id] = min(100, levels[bin_id] + random.choice([0, 1, 2, 3]))
        r = requests.post(URL.format(bin_id), json={"level": levels[bin_id], "lid_open": False,
                                                     "rssi": random.randint(-75, -50)},
                          headers={"X-Device-Token": TOKEN}, timeout=5)
        print(bin_id, levels[bin_id], r.status_code)
    time.sleep(3)
