import requests
import time
import os
import json
from datetime import datetime

# =========================
# CONFIG
# =========================
LOCATION_ID = 5020
# used only if running locally (not needed in GitHub Actions)
CHECK_INTERVAL = 60

STATE_FILE = "state.json"

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


# =========================
# STATE MANAGEMENT
# =========================
def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# =========================
# SLACK ALERT
# =========================
def send_slack(messages):
    if not SLACK_WEBHOOK_URL:
        print("No Slack webhook configured")
        return

    text = "🚨 *NEXUS Slot Update Detected*\n\n"
    text += "\n".join(messages)

    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
    except Exception as e:
        print("Slack error:", e)


# =========================
# FETCH SLOTS
# =========================
def check_slots():
    url = f"https://ttp.cbp.dhs.gov/schedulerapi/locations/{LOCATION_ID}/slots"

    params = {
        "startTimestamp": "2026-05-01T00:00:00",
        "endTimestamp": "2026-07-01T00:00:00"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        slots = []

        for slot in data:
            ts = slot.get("timestamp")
            active = slot.get("active", 0)

            if not ts:
                continue

            date_obj = datetime.fromisoformat(ts.replace("Z", ""))

            # weekend filter
            weekday = date_obj.weekday()
            if weekday >= 5:
                slots.append({
                    "timestamp": ts,
                    "active": active,
                    "weekday": weekday
                })

        return slots

    except Exception as e:
        print("Error:", e)
        return []


# =========================
# MAIN LOGIC (STATEFUL)
# =========================
def run_once():
    print("Checking slots...")

    previous_state = load_state()

    slots = check_slots()

    alerts = []

    for s in slots:
        ts = s["timestamp"]
        active = s["active"]
        weekday = s["weekday"] + 1

        prev = previous_state.get(ts, 0)

        # detect increase ONLY
        if active > prev:
            alerts.append(f"{ts} | wkday: {weekday} | {prev} → {active}")

        # ALWAYS update state
        previous_state[ts] = active

    if alerts:
        print("Alerts:", alerts)
        send_slack(alerts)
    else:
        print("No changes")

    save_state(previous_state)


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    run_once()
