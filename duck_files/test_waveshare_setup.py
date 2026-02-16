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
    from scservo_sdk import PortHandler, sms_sts
    from scservo_sdk.scservo_def import COMM_SUCCESS
except ImportError as e:
    print(f"ERROR: Could not import scservo_sdk: {e}")
    print(f"SDK path: {SDK_PATH}")
    print("Make sure Waveshare SDK is in Python path.")
    sys.exit(1)


class WaveshareTest:
    def __init__(self, port, baudrate=1000000):
        self.port = port
        self.baudrate = baudrate
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
        
        self.packet_handler = sms_sts(self.port_handler)
        return True
    
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
                    degrees = (pos / 2048.0) * 360.0
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
            print(f"Servo {servo_id} not found. Run discovery first.")
            return False
        
        print(f"Moving servo {servo_id} to position {position}...")
        print(f"Duration: {duration}s")
        
        try:
            speed = 500  # Default speed
            acceleration = 30  # Default acceleration
            
            # Send command
            self.packet_handler.WritePosEx(servo_id, position, speed, acceleration)
            print(f"  ✓ Command sent")
            
            # Wait for movement
            time.sleep(duration)
            
            # Read back position
            pos, comm_result, error = self.packet_handler.ReadPos(servo_id)
            if comm_result == COMM_SUCCESS:
                degrees = (pos / 2048.0) * 360.0
                print(f"  ✓ Servo reports position: {pos} ({degrees:.1f}°)")
                
                # Check if close to target
                tolerance = 20  # ±20 units
                if abs(pos - position) <= tolerance:
                    print(f"✓ Movement successful (within tolerance)")
                    return True
                else:
                    print(f"⚠ Position error: expected {position}, got {pos}")
                    return False
            else:
                print(f"✗ Failed to read position (comm_result={comm_result})")
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
                    self.packet_handler.WritePosEx(servo_id, 1024, 500, 30)
                time.sleep(1)
                
                # Move to low position
                print("  Moving to low (512)...")
                for servo_id in servo_ids:
                    self.packet_handler.WritePosEx(servo_id, 512, 500, 30)
                time.sleep(1)
                
                # Move to high position
                print("  Moving to high (1536)...")
                for servo_id in servo_ids:
                    self.packet_handler.WritePosEx(servo_id, 1536, 500, 30)
                time.sleep(1)
            
            # Return to center
            print("\nReturning all servos to center...")
            for servo_id in servo_ids:
                self.packet_handler.WritePosEx(servo_id, 1024, 500, 30)
            
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
    
    args = parser.parse_args()
    
    # Create tester
    tester = WaveshareTest(args.port)
    
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
