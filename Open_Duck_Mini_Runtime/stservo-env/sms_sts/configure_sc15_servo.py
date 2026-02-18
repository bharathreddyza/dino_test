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
parser.add_argument("--only_id", action="store_true", help="Only set ID; skip centering and movement verification")
args = parser.parse_args()

print("\n=== SC-15 Servo Configuration ===")
print("⚠️  Ensure ONLY ONE SERVO is connected")
print("================================\n")

# Initialize port
portHandler = PortHandler(DEVICENAME)
# Use SCSCL handler for SC-15 servos (SC protocol)
packetHandler = scscl(portHandler)

# ID register address for SC servos
ID_ADDR = 5

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

# ---------- Move to center (optional) ----------
if not args.only_id:
    print(f"\nMoving servo ID {found_id} to CENTER ({CENTER_POS})")
    packetHandler.WritePos(found_id, CENTER_POS, MOVE_SPEED, MOVE_ACC)
    time.sleep(2)

    print("\n➡️  POWER OFF NOW")
    print("➡️  Mount horn at mechanical neutral")
    input("Press ENTER after mounting horn...")
else:
    print("\n--only_id set: skipping centering and horn mounting prompt")

# ---------- Assign new ID ----------
if found_id != args.new_id:
    print(f"\nChanging ID {found_id} → {args.new_id}")

    # Read current ID register for debug
    cur_id_val, res_cur, err_cur = packetHandler.read1ByteTxRx(found_id, ID_ADDR)
    print(f"Current ID register (at {found_id}): read={cur_id_val} (res={res_cur}, err={err_cur})")

    # Unlock EPROM so the ID write is persisted
    print("Unlocking EPROM...")
    res_unlock, err_unlock = packetHandler.unLockEprom(found_id)
    if res_unlock != COMM_SUCCESS:
        print(f"❌ Failed to unlock EPROM (result={res_unlock}, err={err_unlock})")
        portHandler.closePort()
        quit()

    # Write new ID to EPROM (write to current address)
    print(f"Writing new ID {args.new_id} to address {ID_ADDR} at servo {found_id}...")
    res_write, err_write = packetHandler.write1ByteTxRx(found_id, ID_ADDR, args.new_id)
    time.sleep(0.8)
    if res_write != COMM_SUCCESS:
        print(f"❌ Failed to write new ID (result={res_write}, err={err_write})")
        portHandler.closePort()
        quit()

    # Redundant write and small delay to improve persistence on flaky units
    print("Performing redundant write to increase chance of EPROM commit...")
    res_write2, err_write2 = packetHandler.write1ByteTxRx(found_id, ID_ADDR, args.new_id)
    time.sleep(0.8)
    print(f"Write results: first={res_write}, second={res_write2}")
    if res_write2 != COMM_SUCCESS:
        print(f"⚠ Second write failed (result={res_write2}, err={err_write2})")

    # After writing, attempt to lock EPROM. Try locking using the new ID first, fall back to old ID.
    print("Locking EPROM (try new ID)...")
    res_lock, err_lock = packetHandler.LockEprom(args.new_id)
    print(f"Lock attempt result (new ID): res={res_lock}, err={err_lock}")
    if res_lock != COMM_SUCCESS:
        print("Lock with new ID failed, trying lock with old ID...")
        res_lock_old, err_lock_old = packetHandler.LockEprom(found_id)
        print(f"Lock old ID result: {res_lock_old}, err={err_lock_old}")

    # Give EPROM time to settle before closing or power-cycling
    time.sleep(1.2)
    if res_lock != COMM_SUCCESS:
        print(f"⚠️  Warning: failed to lock EPROM (result={res_lock}, err={err_lock})")

    # Verify new ID by reading it back from both old and new addresses
    time.sleep(0.5)
    new_id_val, res_read, err_read = packetHandler.read1ByteTxRx(args.new_id, ID_ADDR)
    old_id_val, res_old_read, err_old_read = packetHandler.read1ByteTxRx(found_id, ID_ADDR)
    print(f"Read at new ID {args.new_id}: {new_id_val} (res={res_read}, err={err_read})")
    print(f"Read at old ID {found_id}: {old_id_val} (res={res_old_read}, err={err_old_read})")
    if res_read == COMM_SUCCESS and new_id_val == args.new_id:
        print(f"✔ ID successfully set to {new_id_val}")
        current_id = args.new_id
    else:
        print(f"❌ Verification failed: read={new_id_val} (result={res_read}, err={err_read})")
        portHandler.closePort()
        quit()
else:
    current_id = found_id
    print("ID already correct, skipping ID change")

# ---------- Verification (optional) ----------
if not args.only_id:
    print("\nVerifying motion...")
    packetHandler.WritePos(current_id, TEST_LEFT, MOVE_SPEED, MOVE_ACC)
    time.sleep(1)
    packetHandler.WritePos(current_id, TEST_RIGHT, MOVE_SPEED, MOVE_ACC)
    time.sleep(1)
    packetHandler.WritePos(current_id, CENTER_POS, MOVE_SPEED, MOVE_ACC)
    time.sleep(1)
else:
    print("--only_id set: skipping motion verification")

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
