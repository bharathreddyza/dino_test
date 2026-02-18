#!/usr/bin/env python3
"""
Waveshare Servo Integration Test Suite
========================================

Quick diagnostic tests to validate Waveshare servo setup
before running the full RL policy.

Usage:
    python test_waveshare_setup.py --port COM5 --test all
    python test_waveshare_setup.py --port /dev/ttyACM0 --test discovery
    python test_waveshare_setup.py --port COM5 --test movement
"""

import sys
import os
import time
import argparse
import numpy as np

# Add SDK paths
SDK_PATH = os.path.join(
    os.path.dirname(__file__), 
    "..", "..", "..", 
    "STServo_Python", 
    "stservo-env"
)
if os.path.exists(SDK_PATH):
    sys.path.insert(0, SDK_PATH)

try:
    from scservo_sdk import PortHandler, sms_sts, scscl
    from scservo_sdk.scservo_def import COMM_SUCCESS, COMM_RX_TIMEOUT
except ImportError as e:
    print(f"ERROR: Could not import scservo_sdk: {e}")
    print(f"SDK path: {SDK_PATH}")
    print("Make sure Waveshare SDK is in Python path.")
    sys.exit(1)


class WaveshareTest:
    def __init__(self, port, baudrate=1000000, protocol="sms_sts"):
        self.port = port
        self.baudrate = baudrate
        self.protocol = protocol
        self.port_handler = None
        self.packet_handler = None
        self.detected_servos = {}
        
    def open_connection(self):
        """Open serial port and initialize packet handler"""
        print(f"Opening port {self.port}...")
        self.port_handler = PortHandler(self.port)
        
        if not self.port_handler.openPort():
            print(f"  ✗ Failed to open port {self.port}")
            return False
        
        print(f"  ✓ Port opened")
        
        if not self.port_handler.setBaudRate(self.baudrate):
            print(f"  ✗ Failed to set baud rate {self.baudrate}")
            return False
        
        print(f"  ✓ Baud rate set to {self.baudrate}")
        
        # choose handler according to protocol
        if self.protocol == "scscl":
            self.packet_handler = scscl(self.port_handler)
        else:
            self.packet_handler = sms_sts(self.port_handler)
        return True

    def normalize_position(self, raw_pos):
        """Convert raw position to signed host value when needed."""
        try:
            return self.packet_handler.scs_tohost(raw_pos, 15)
        except Exception:
            return raw_pos

    def position_to_degrees(self, pos):
        """Convert a raw position count to degrees depending on protocol.
        - SC (scscl): 180° == 1024 counts (servo mode)
        - ST/SMS (sms_sts): 360° == 2048 counts
        """
        if self.protocol == "scscl":
            return (pos / 1024.0) * 180.0
        else:
            return (pos / 2048.0) * 360.0

    def write_position(self, servo_id, position, speed, acc):
        """Write a position using the appropriate API on the packet handler."""
        # scscl.WritePos signature: (id, position, time, speed)
        # sms_sts.WritePosEx signature: (id, position, speed, acc)
        if self.protocol == "scscl" and hasattr(self.packet_handler, "WritePos"):
            # Follow Arduino example: use time=0 and a higher default speed if caller passed a small value.
            time_param = 0
            speed_param = speed
            if not isinstance(speed_param, int) or speed_param < 1000:
                speed_param = 1500
            return self.packet_handler.WritePos(servo_id, position, time_param, speed_param)
        elif hasattr(self.packet_handler, "WritePosEx"):
            return self.packet_handler.WritePosEx(servo_id, position, speed, acc)
        else:
            # Fallback: try whichever is available
            if hasattr(self.packet_handler, "WritePos"):
                return self.packet_handler.WritePos(servo_id, position, 0, speed)
            return None
    
    def close_connection(self):
        """Close serial port"""
        if self.port_handler:
            self.port_handler.closePort()
            print("Port closed")
    
    def test_discovery(self):
        """Test 1: Servo discovery"""
        print("\n" + "="*60)
        print("TEST 1: SERVO DISCOVERY")
        print("="*60)
        
        expected_ids = [10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33]
        found_count = 0
        
        print("Scanning ID range 0-254...")
        
        for servo_id in range(0, 254):
            try:
                pos, comm_result, error = self.packet_handler.ReadPos(servo_id)
                if comm_result == COMM_SUCCESS:
                    pos = self.normalize_position(pos)
                    self.detected_servos[servo_id] = pos
                    print(f"  ✓ ID {servo_id:3d}: position = {pos:4d}")
                    found_count += 1
            except Exception as e:
                pass
        
        print(f"\nFound {found_count} servo(s)")
        
        # Check if expected servos are present
        missing = [id for id in expected_ids if id not in self.detected_servos]
        if missing:
            print(f"⚠ Missing expected servos: {missing}")
            return False
        
        print("✓ All expected servos found!")
        return True
    
    def test_read_positions(self):
        """Test 2: Read positions from all servos"""
        print("\n" + "="*60)
        print("TEST 2: READ POSITIONS")
        print("="*60)
        
        if not self.detected_servos:
            print("No servos detected. Run discovery test first.")
            return False
        
        print("Reading positions from all detected servos...\n")
        print("Servo ID | Position | Degrees")
        print("-" * 35)
        
        all_ok = True
        for servo_id in sorted(self.detected_servos.keys()):
            try:
                pos, comm_result, error = self.packet_handler.ReadPos(servo_id)
                if comm_result == COMM_SUCCESS:
                    pos = self.normalize_position(pos)
                    degrees = self.position_to_degrees(pos)
                    print(f"  {servo_id:3d}    | {pos:4d}     | {degrees:6.1f}°")
                else:
                    print(f"  {servo_id:3d}    | ERROR (comm_result={comm_result})")
                    all_ok = False
            except Exception as e:
                print(f"  {servo_id:3d}    | EXCEPTION: {e}")
                all_ok = False
        
        return all_ok
    
    def test_read_speeds(self):
        """Test 3: Read speeds from all servos"""
        print("\n" + "="*60)
        print("TEST 3: READ SPEEDS")
        print("="*60)
        
        if not self.detected_servos:
            print("No servos detected. Run discovery test first.")
            return False
        
        print("Reading speeds from all detected servos...\n")
        print("Servo ID | Speed (raw)")
        print("-" * 25)
        
        all_ok = True
        for servo_id in sorted(self.detected_servos.keys()):
            try:
                speed, comm_result, error = self.packet_handler.ReadSpeed(servo_id)
                if comm_result == COMM_SUCCESS:
                    print(f"  {servo_id:3d}    | {speed}")
                else:
                    print(f"  {servo_id:3d}    | ERROR (comm_result={comm_result})")
                    all_ok = False
            except Exception as e:
                print(f"  {servo_id:3d}    | EXCEPTION: {e}")
                all_ok = False
        
        return all_ok
    
    def test_single_movement(self, servo_id, position, duration=1.0):
        """Test 4: Move a single servo"""
        print("\n" + "="*60)
        print(f"TEST 4: SINGLE SERVO MOVEMENT (ID {servo_id})")
        print("="*60)
        
        if servo_id not in self.detected_servos:
            print(f"Servo {servo_id} not found in memory — running discovery now...")
            # Attempt discovery now to populate detected_servos
            ok = self.test_discovery()
            if not ok or servo_id not in self.detected_servos:
                print(f"Servo {servo_id} still not found after discovery. Aborting.")
                return False
        
        print(f"Moving servo {servo_id} to position {position}...")
        print(f"Duration: {duration}s")
        
        try:
            speed = 500  # Default speed
            acceleration = 30  # Default acceleration
            
            # Read current position to estimate move time and to fetch limits
            pos_before = None
            try:
                p_before, r_before, e_before = self.packet_handler.ReadPos(servo_id)
                if r_before == COMM_SUCCESS:
                    pos_before = self.normalize_position(p_before)
                else:
                    pos_before = None
            except Exception:
                pos_before = None
            # For SC servos, fetch min/max angle limits so we clamp target
            min_ang = None
            max_ang = None
            try:
                ma, rma, ema = self.packet_handler.read2ByteTxRx(servo_id, 9)
                Mi, rmi, emi = self.packet_handler.read2ByteTxRx(servo_id, 11)
                if rma == COMM_SUCCESS and rmi == COMM_SUCCESS:
                    min_ang = ma
                    max_ang = Mi
            except Exception:
                pass

            # Send command and check result
            # Clamp requested position to limits when available
            req_pos = position
            if min_ang is not None and max_ang is not None:
                if req_pos < min_ang:
                    print(f"Requested pos {req_pos} below min {min_ang}, clamping")
                    req_pos = min_ang
                if req_pos > max_ang:
                    print(f"Requested pos {req_pos} above max {max_ang}, clamping")
                    req_pos = max_ang

            # For scscl, compute time parameter from delta and call WritePos directly
            if self.protocol == "scscl" and hasattr(self.packet_handler, "WritePos"):
                cur = pos_before if pos_before is not None else req_pos
                delta = abs(cur - req_pos)
                # time in ms = (delta / speed) * 1000 + 100 (Arduino example)
                spd = speed if isinstance(speed, (int, float)) and speed > 0 else 1500
                time_param = int((delta / max(spd, 1.0)) * 1000.0) + 100
                if time_param < 100:
                    time_param = 100
                speed_param = spd if spd >= 1000 else 1500
                write_res = self.packet_handler.WritePos(servo_id, req_pos, time_param, speed_param)
            else:
                write_res = self.write_position(servo_id, req_pos, speed, acceleration)
            # write_res may be (result, error) or COMM_SUCCESS int; normalize
            write_result = None
            write_error = None
            if isinstance(write_res, tuple) and len(write_res) >= 1:
                write_result = write_res[0]
                write_error = write_res[1] if len(write_res) > 1 else None
            elif isinstance(write_res, int):
                write_result = write_res

            if write_result is not None and write_result != COMM_SUCCESS:
                print(f"✗ Write failed (result={write_result}, err={write_error})")
                return False

            print(f"  ✓ Command sent (write_result={write_result})")

            # Estimate wait time from position delta and speed (seconds)
            if pos_before is not None:
                delta = abs(pos_before - position)
                est_wait = delta / max(speed, 1) + 0.1
            else:
                est_wait = max(duration, 0.5)

            max_wait = min(max(est_wait * 3, 0.5), 8.0)

            # Poll ReadMoving until movement stops or timeout
            moved = True
            start_t = time.time()
            while time.time() - start_t < max_wait:
                try:
                    moving, rmove, emove = self.packet_handler.ReadMoving(servo_id)
                    if rmove == COMM_SUCCESS:
                        if moving == 0:
                            moved = False
                            break
                    # else: fall through and wait
                except Exception:
                    pass
                time.sleep(0.05)

            if moved:
                # give a small extra delay before final read
                time.sleep(0.1)

            # Read back position with retries
            pos = None
            comm_result = COMM_RX_TIMEOUT
            error = None
            for attempt in range(6):
                try:
                    pos, comm_result, error = self.packet_handler.ReadPos(servo_id)
                    if comm_result == COMM_SUCCESS:
                        break
                except Exception:
                    comm_result = COMM_RX_TIMEOUT
                    error = None
                time.sleep(0.1)
            if comm_result == COMM_SUCCESS:
                pos = self.normalize_position(pos)
                degrees = self.position_to_degrees(pos)
                print(f"  ✓ Servo reports position: {pos} ({degrees:.1f}°)")
                
                # Check if close to target
                tolerance = 20  # ±20 units
                if abs(pos - position) <= tolerance:
                    print(f"✓ Movement successful (within tolerance)")
                    return True
                else:
                    print(f"⚠ Position error: expected {position}, got {pos}")
                    print("Collecting debug registers...")
                    try:
                        # Read some control registers for diagnosis (use 2-byte reads where appropriate)
                        regs = {}
                        # Torque enable (1 byte)
                        te, r_te, e_te = self.packet_handler.read1ByteTxRx(servo_id, 40)
                        regs['torque_enable'] = (te, r_te, e_te)
                        # Offset (2 bytes)
                        ofs, r_ofs, e_ofs = self.packet_handler.read2ByteTxRx(servo_id, 31)
                        regs['offset'] = (ofs, r_ofs, e_ofs)
                        # Mode (1 byte)
                        mode, r_mode, e_mode = self.packet_handler.read1ByteTxRx(servo_id, 33)
                        regs['mode'] = (mode, r_mode, e_mode)
                        # Min/Max angle limits (2 bytes each)
                        min_ang, r_min, e_min = self.packet_handler.read2ByteTxRx(servo_id, 9)
                        max_ang, r_max, e_max = self.packet_handler.read2ByteTxRx(servo_id, 11)
                        regs['min_angle'] = (min_ang, r_min, e_min)
                        regs['max_angle'] = (max_ang, r_max, e_max)
                        # Goal position and speed (2 bytes)
                        gp, r_gp, e_gp = self.packet_handler.read2ByteTxRx(servo_id, 42)
                        gs, r_gs, e_gs = self.packet_handler.read2ByteTxRx(servo_id, 46)
                        regs['goal_pos'] = (gp, r_gp, e_gp)
                        regs['goal_spd'] = (gs, r_gs, e_gs)
                        # Print
                        for k, v in regs.items():
                            print(f"  {k}: {v}")
                    except Exception as e:
                        print(f"  Debug read failed: {e}")
                    return False
            else:
                # try verbose fallback: ReadPosSpeed
                try:
                    p, s, rps, eps = self.packet_handler.ReadPosSpeed(servo_id)
                    if rps == COMM_SUCCESS:
                        p = self.normalize_position(p)
                        print(f"  ✓ ReadPosSpeed fallback: pos={p}, spd={s}")
                        pos = p
                        comm_result = rps
                    else:
                        print(f"✗ Failed to read position (comm_result={comm_result})")
                        return False
                except Exception as e:
                    print(f"✗ Failed to read position (comm_result={comm_result}), exception: {e}")
                    return False
                
        except Exception as e:
            print(f"✗ Exception: {e}")
            return False
    
    def test_all_movement(self, num_cycles=3):
        """Test 5: Move all servos in sequence"""
        print("\n" + "="*60)
        print("TEST 5: ALL SERVOS MOVEMENT")
        print("="*60)
        
        if not self.detected_servos:
            print("No servos detected. Run discovery first.")
            return False
        
        servo_ids = sorted(self.detected_servos.keys())
        print(f"Moving {len(servo_ids)} servos in {num_cycles} cycles...")
        
        try:
            for cycle in range(num_cycles):
                print(f"\nCycle {cycle + 1}/{num_cycles}")
                
                # Move to center position
                print("  Moving to center (1024)...")
                for servo_id in servo_ids:
                    self.write_position(servo_id, 1024, 500, 30)
                time.sleep(1)
                
                # Move to low position
                print("  Moving to low (512)...")
                for servo_id in servo_ids:
                    self.write_position(servo_id, 512, 500, 30)
                time.sleep(1)
                
                # Move to high position
                print("  Moving to high (1536)...")
                for servo_id in servo_ids:
                    self.write_position(servo_id, 1536, 500, 30)
                time.sleep(1)
            
            # Return to center
            print("\nReturning all servos to center...")
            for servo_id in servo_ids:
                self.write_position(servo_id, 1024, 500, 30)
            
            print("✓ All movement cycles completed")
            return True
            
        except Exception as e:
            print(f"✗ Exception: {e}")
            return False
    
    def test_hwi_interface(self):
        """Test 6: Test WaveshareHWI class if duck_config available"""
        print("\n" + "="*60)
        print("TEST 6: WAVESHARE HWI INTERFACE")
        print("="*60)
        
        try:
            from mini_bdx_runtime.duck_config import DuckConfig
            from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI
        except ImportError as e:
            print(f"Could not import HWI: {e}")
            print("Skipping this test.")
            return None
        
        try:
            # Try to find duck_config.json
            config_path = os.path.expanduser("~/duck_config.json")
            if not os.path.exists(config_path):
                config_path = "mini_bdx_runtime/assets/duck_config.json"
            
            if not os.path.exists(config_path):
                print(f"Could not find duck_config.json")
                print(f"Tried: {config_path}")
                return None
            
            print(f"Loading config from: {config_path}")
            config = DuckConfig(config_path)
            
            # Close existing connection
            self.close_connection()
            
            # Create HWI instance
            print("Initializing WaveshareHWI...")
            hwi = WaveshareHWI(config, usb_port=self.port)
            
            print("✓ HWI initialized successfully")
            
            # Test position reading
            print("Reading positions via HWI...")
            positions = hwi.get_present_positions()
            if positions is not None:
                print(f"✓ Got positions: shape={positions.shape}")
                print(f"  Sample values: {positions[:3]}")
            else:
                print("✗ Failed to read positions")
                hwi.close()
                return False
            
            hwi.close()
            
            # Reopen connection for other tests
            self.open_connection()
            return True
            
        except Exception as e:
            print(f"✗ Exception: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Waveshare Servo Setup Diagnostic Tests"
    )
    parser.add_argument(
        "--port",
        type=str,
        default="COM5",
        help="Serial port (default: COM5)"
    )
    parser.add_argument(
        "--test",
        type=str,
        default="all",
        choices=["all", "discovery", "positions", "speeds", "single", "all_move", "hwi"],
        help="Which test(s) to run"
    )
    parser.add_argument(
        "--servo-id",
        type=int,
        default=10,
        help="Servo ID for single movement test"
    )
    parser.add_argument(
        "--position",
        type=int,
        default=1024,
        help="Target position for single movement test"
    )
    parser.add_argument(
        "--protocol",
        type=str,
        default="sms_sts",
        choices=["sms_sts", "scscl"],
        help="Which servo protocol/handler to use (default: sms_sts)"
    )
    
    args = parser.parse_args()
    
    # Create tester
    tester = WaveshareTest(args.port, protocol=args.protocol)
    
    # Open connection
    if not tester.open_connection():
        print("Failed to open connection. Exiting.")
        sys.exit(1)
    
    print(f"✓ Connected to {args.port} @ {tester.baudrate} bps\n")
    
    # Run tests
    results = {}
    
    try:
        if args.test in ["all", "discovery"]:
            results["discovery"] = tester.test_discovery()
        
        if args.test in ["all", "positions"]:
            results["positions"] = tester.test_read_positions()
        
        if args.test in ["all", "speeds"]:
            results["speeds"] = tester.test_read_speeds()
        
        if args.test in ["all", "single"]:
            results["single"] = tester.test_single_movement(
                args.servo_id, 
                args.position
            )
        
        if args.test in ["all", "all_move"]:
            results["all_move"] = tester.test_all_movement()
        
        if args.test in ["all", "hwi"]:
            results["hwi"] = tester.test_hwi_interface()
    
    finally:
        tester.close_connection()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⊘ SKIP"
        print(f"{test_name:20s}: {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
