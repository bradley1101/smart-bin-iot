"""Smart bin supervision server.

  POST /api/bins/<id>/telemetry   (ESP32, header X-Device-Token)  {"level": 0-100, "lid_open": bool, "rssi": int}
  GET  /api/bins                  status of every bin
  GET  /api/bins/<id>/history     readings of the last N hours (?hours=24)
  GET  /api/events                latest alerts / collections
  GET  /                          controller dashboard
  GET  /collecte                  collectors' mobile page (bins to empty)
"""
import os
from datetime import datetime, timedelta, timezone

from flask import Flask, abort, jsonify, render_template, request

import db
from notifier import WhatsAppNotifier


def utcnow():
    return datetime.now(timezone.utc)


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("DATABASE", os.path.join(app.root_path, "smartbin.db")),
        DEVICE_TOKEN=os.environ.get("DEVICE_TOKEN", "change-me"),
        ALERT_PCT=int(os.environ.get("ALERT_PCT", 90)),     # WhatsApp alert threshold
        FULL_PCT=int(os.environ.get("FULL_PCT", 85)),       # "full" on the dashboard
        EMPTIED_PCT=int(os.environ.get("EMPTIED_PCT", 20)), # below: the bin was emptied
        OFFLINE_S=int(os.environ.get("OFFLINE_S", 120)),
    )
    if test_config:
        app.config.update(test_config)
    app.notifier = (test_config or {}).get("NOTIFIER") or WhatsAppNotifier()

    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

    # ------------------------------------------------------------ helpers
    def status_of(level, last_ts):
        if last_ts is None:
            return "unknown"
        if (utcnow() - parse_ts(last_ts)).total_seconds() > app.config["OFFLINE_S"]:
            return "offline"
        if level >= app.config["FULL_PCT"]:
            return "full"
        if level >= 50:
            return "half"
        return "ok"

    def bin_rows():
        rows = db.get_db().execute("""
            SELECT b.id, b.name, b.location, b.alert_sent,
                   r.level, r.lid_open, r.rssi, r.ts
            FROM bins b
            LEFT JOIN readings r ON r.id = (SELECT MAX(id) FROM readings WHERE bin_id = b.id)
            ORDER BY b.id""").fetchall()
        out = []
        for r in rows:
            level = r["level"] if r["level"] is not None else 0
            out.append({
                "id": r["id"], "name": r["name"], "location": r["location"],
                "level": r["level"], "lid_open": bool(r["lid_open"]), "rssi": r["rssi"],
                "last_seen": r["ts"], "alert_sent": bool(r["alert_sent"]),
                "status": status_of(level, r["ts"]),
            })
        return out

    def evaluate_alert(bin_row, level):
        """WhatsApp once per fill cycle: armed again when the bin has been emptied."""
        conn = db.get_db()
        if level >= app.config["ALERT_PCT"] and not bin_row["alert_sent"]:
            text = (f"🗑️ {bin_row['name']} ({bin_row['location']}) est pleine à {level} %. "
                    f"Merci de passer la vider.")
            result = app.notifier.send(text)
            conn.execute("UPDATE bins SET alert_sent = 1 WHERE id = ?", (bin_row["id"],))
            conn.execute("INSERT INTO events (bin_id, kind, level, detail) VALUES (?, 'FULL_ALERT', ?, ?)",
                         (bin_row["id"], level, f"WhatsApp: {result}"))
        elif level <= app.config["EMPTIED_PCT"] and bin_row["alert_sent"]:
            conn.execute("UPDATE bins SET alert_sent = 0 WHERE id = ?", (bin_row["id"],))
            conn.execute("INSERT INTO events (bin_id, kind, level, detail) VALUES (?, 'EMPTIED', ?, ?)",
                         (bin_row["id"], level, "collecte effectuée"))

    # ---------------------------------------------------------------- API
    @app.post("/api/bins/<bin_id>/telemetry")
    def telemetry(bin_id):
        if request.headers.get("X-Device-Token") != app.config["DEVICE_TOKEN"]:
            abort(401)
        conn = db.get_db()
        bin_row = conn.execute("SELECT * FROM bins WHERE id = ?", (bin_id,)).fetchone()
        if bin_row is None:
            abort(404)
        data = request.get_json(silent=True) or {}
        level = data.get("level")
        if not isinstance(level, int) or not 0 <= level <= 100:
            return jsonify(error="level must be an integer between 0 and 100"), 400
        conn.execute("INSERT INTO readings (bin_id, level, lid_open, rssi) VALUES (?, ?, ?, ?)",
                     (bin_id, level, int(bool(data.get("lid_open"))), data.get("rssi")))
        evaluate_alert(bin_row, level)
        conn.commit()
        return jsonify(ok=True)

    @app.get("/api/bins")
    def bins():
        return jsonify(bin_rows())

    @app.get("/api/bins/<bin_id>/history")
    def history(bin_id):
        hours = min(int(request.args.get("hours", 24)), 24 * 7)
        since = (utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = db.get_db().execute(
            "SELECT ts, level FROM readings WHERE bin_id = ? AND ts >= ? ORDER BY ts", (bin_id, since)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/events")
    def events():
        rows = db.get_db().execute("""
            SELECT e.ts, e.kind, e.level, e.detail, b.name
            FROM events e JOIN bins b ON b.id = e.bin_id
            ORDER BY e.ts DESC, e.id DESC LIMIT 20""").fetchall()
        return jsonify([dict(r) for r in rows])

    # ---------------------------------------------------------------- pages
    @app.get("/")
    def dashboard():
        return render_template("index.html", alert_pct=app.config["ALERT_PCT"],
                               whatsapp=app.notifier.configured)

    @app.get("/collecte")
    def collecte():
        return render_template("collecte.html", full_pct=app.config["FULL_PCT"])

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=False)
