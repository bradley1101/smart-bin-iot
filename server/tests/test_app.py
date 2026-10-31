import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app  # noqa: E402
from notifier import WhatsAppNotifier  # noqa: E402

TOKEN = {"X-Device-Token": "test-token"}


@pytest.fixture
def client(tmp_path):
    notifier = WhatsAppNotifier(recipients="")
    app = create_app({"DATABASE": str(tmp_path / "t.db"), "DEVICE_TOKEN": "test-token",
                      "NOTIFIER": notifier, "TESTING": True})
    c = app.test_client()
    c.notifier = notifier
    return c


def post(client, level, bin_id="bin-1", headers=TOKEN):
    return client.post(f"/api/bins/{bin_id}/telemetry", json={"level": level, "lid_open": False}, headers=headers)


def test_rejects_missing_token(client):
    assert post(client, 50, headers={}).status_code == 401


def test_rejects_unknown_bin_and_bad_level(client):
    assert post(client, 50, bin_id="bin-99").status_code == 404
    assert post(client, 150).status_code == 400
    assert post(client, "50").status_code == 400


def test_status_follows_level(client):
    post(client, 30)
    post(client, 88, bin_id="bin-2")
    bins = {b["id"]: b for b in client.get("/api/bins").get_json()}
    assert bins["bin-1"]["status"] == "ok" and bins["bin-1"]["level"] == 30
    assert bins["bin-2"]["status"] == "full"


def test_whatsapp_alert_sent_once_per_fill_cycle(client):
    for level in (70, 91, 95, 99):
        post(client, level)
    assert len(client.notifier.sent) == 1
    assert "Poubelle 1" in client.notifier.sent[0] and "91 %" in client.notifier.sent[0]

    post(client, 5)            # emptied by the collector -> alert re-armed
    post(client, 92)
    assert len(client.notifier.sent) == 2

    kinds = [e["kind"] for e in client.get("/api/events").get_json()]
    assert kinds == ["FULL_ALERT", "EMPTIED", "FULL_ALERT"]


def test_history_and_pages(client):
    post(client, 10)
    post(client, 20)
    assert [p["level"] for p in client.get("/api/bins/bin-1/history").get_json()] == [10, 20]
    assert client.get("/").status_code == 200
    assert client.get("/collecte").status_code == 200


def test_offline_when_no_recent_data(client, monkeypatch):
    post(client, 40)
    import app as app_module
    from datetime import timedelta
    real = app_module.utcnow
    monkeypatch.setattr(app_module, "utcnow", lambda: real() + timedelta(minutes=10))
    assert client.get("/api/bins").get_json()[0]["status"] == "offline"
