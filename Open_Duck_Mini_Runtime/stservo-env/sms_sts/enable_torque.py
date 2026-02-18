import time
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

p = PortHandler("COM5")
p.openPort()
p.setBaudRate(1000000)

Scscl = scscl.scscl if hasattr(scscl, "scscl") else scscl
pkt = Scscl(p)

sid = 21
pkt.write1ByteTxRx(sid, 40, 1)   # write torque enable = 1
print(f"Enabled torque on {sid}")

p.closePort()