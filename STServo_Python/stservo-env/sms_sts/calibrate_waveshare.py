"""Simple calibration helper: move each servo to center and read counts.

Produces a JSON mapping of ``id -> observed_count`` which can be used to
compute offsets for `duck_config.json` or a separate calibration file.
"""
import time
import json
from scservo_sdk import PortHandler
from scservo_sdk import scscl

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
