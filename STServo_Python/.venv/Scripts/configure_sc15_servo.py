#!/usr/bin/env python3
"""
SC-15 Serial Bus Servo Setup Script (Protocol ST)

- One servo at a time
- Center servo
- Mount horn
- Assign new ID
- Verify motion

Requires: scservo_sdk
"""

import time
import argparse
import sys
import os

if os.name == 'nt':
    import msvcrt
    def getch():
        return msvcrt.getch().decode()
        
else:
    import sys, tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

sys.path.append("..")


from scservo_sdk import *

# ---------------- USER CONFIG ----------------
BAUDRATE   = 1_000_000
DEVICENAME = "COM5"          # change if needed

CENTER_POS = 512             # 180° / 1024 resolution
TEST_LEFT  = 420
TEST_RIGHT = 600

MOVE_SPEED = 600             # safe bench speed
MOVE_ACC   = 30              # soft accel
SCAN_RANGE = range(0, 254)   # valid ID range
# ---------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument("--new_id", type=int, required=True, help="New ID for this servo (0–253)")
args = parser.parse_args()

print("\n=== SC-15 Servo Configuration ===")
print("⚠️  Ensure ONLY ONE SERVO is connected")
print("================================\n")

# Initialize port
portHandler = PortHandler(DEVICENAME)
packetHandler = sms_sts(portHandler)

if not portHandler.openPort():
    print("❌ Failed to open port")
    quit()

if not portHandler.setBaudRate(BAUDRATE):
    print("❌ Failed to set baudrate")
    quit()

print("✔ Port opened, baudrate set")

# ---------- Scan for servo ----------
found_id = None
print("\nScanning for servo ID...")

for sid in SCAN_RANGE:
    try:
        pos, spd, comm, err = packetHandler.ReadPosSpeed(sid)
        if comm == COMM_SUCCESS:
            print(f"✔ Found servo at ID {sid}, position {pos}")
            found_id = sid
            break
    except:
        pass

if found_id is None:
    print("❌ No servo detected. Check power & wiring.")
    portHandler.closePort()
    quit()

# ---------- Move to center ----------
print(f"\nMoving servo ID {found_id} to CENTER ({CENTER_POS})")
packetHandler.WritePosEx(found_id, CENTER_POS, MOVE_SPEED, MOVE_ACC)
time.sleep(2)

print("\n➡️  POWER OFF NOW")
print("➡️  Mount horn at mechanical neutral")
input("Press ENTER after mounting horn...")

# ---------- Assign new ID ----------
if found_id != args.new_id:
    print(f"\nChanging ID {found_id} → {args.new_id}")
    packetHandler.write1ByteTxRx(found_id, SMS_STS_ID, args.new_id)
    time.sleep(1)
    current_id = args.new_id
else:
    current_id = found_id
    print("ID already correct, skipping ID change")

# ---------- Verification ----------
print("\nVerifying motion...")
packetHandler.WritePosEx(current_id, TEST_LEFT, MOVE_SPEED, MOVE_ACC)
time.sleep(1)
packetHandler.WritePosEx(current_id, TEST_RIGHT, MOVE_SPEED, MOVE_ACC)
time.sleep(1)
packetHandler.WritePosEx(current_id, CENTER_POS, MOVE_SPEED, MOVE_ACC)
time.sleep(1)

# ---------- Read feedback ----------
pos, spd, comm, err = packetHandler.ReadPosSpeed(current_id)
# volt, load, comm, err = packetHandler.ReadVoltageLoad(current_id)

print("\n===")
print("Servo configured successfully")
print(f"Final ID: {current_id}")
print(f"Position: {pos}")
# print(f"Voltage : {volt / 10:.1f} V")
# print(f"Load    : {load}")
print("===")

portHandler.closePort()
print("\nYou can now disconnect this servo and move to the next one.")
