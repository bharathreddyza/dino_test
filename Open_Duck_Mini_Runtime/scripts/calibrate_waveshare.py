"""Simple calibration helper: move each servo to center and read counts.

Produces a JSON mapping of ``id -> observed_count`` which can be used to
compute offsets for `duck_config.json` or a separate calibration file.
"""
import time
import json
import os
import sys

# Add SDK paths (try a couple of sensible relative locations)
BASE = os.path.dirname(__file__)
candidate_paths = [
    os.path.join(BASE, "..", "..", "STServo_Python", "stservo-env"),
    os.path.join(BASE, "..", "..", "..", "STServo_Python", "stservo-env"),
]
SDK_PATH = None
for p in candidate_paths:
    p = os.path.normpath(p)
    if os.path.exists(p):
        SDK_PATH = p
        break
if SDK_PATH:
    sys.path.insert(0, SDK_PATH)

try:
    from scservo_sdk import PortHandler, sms_sts, scscl
    from scservo_sdk.scservo_def import COMM_SUCCESS, COMM_RX_TIMEOUT
except ImportError as e:
    print(f"ERROR: Could not import scservo_sdk: {e}")
    print(f"Tried SDK path: {SDK_PATH}")
    print("Make sure Waveshare SDK is in Python path or activate the stservo-env virtualenv.")
    sys.exit(1)

PORT = "COM5"
BAUD = 1000000

def main():
    port = PortHandler(PORT)
    port.openPort()
    port.setBaudRate(BAUD)

    packet = scscl.scscl(port)

    found = []
    print("Scanning IDs 1-50 for present servos...")
    for sid in range(1, 51):
        try:
            _, res, err = packet.ReadPos(sid)
            if res == 0:
                found.append(sid)
        except Exception:
            pass

    print(f"Found servos: {found}")

    results = {}
    for sid in found:
        center = 512
        try:
            packet.WritePos(sid, center, 0, 500)
        except Exception as e:
            print(f"WritePos failed for {sid}: {e}")
            continue
        time.sleep(0.8)
        try:
            pos, _, _ = packet.ReadPos(sid)
            results[sid] = pos
            print(f"Servo {sid} -> observed {pos}")
        except Exception as e:
            print(f"ReadPos failed for {sid}: {e}")

    with open("waveshare_calibration.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Saved waveshare_calibration.json")
    port.closePort()

if __name__ == "__main__":
    main()
