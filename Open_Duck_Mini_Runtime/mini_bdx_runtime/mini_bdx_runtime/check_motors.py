"""
Debug script to check all motors in the robot.
Verifies each motor is accessible and allows testing movement.
"""

import time
import numpy as np
import traceback
import argparse

from mini_bdx_runtime.duck_config import DuckConfig

try:
    from mini_bdx_runtime.rustypot_position_hwi import HWI as RustypotHWI
except Exception:
    RustypotHWI = None

try:
    from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI
except Exception:
    WaveshareHWI = None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duck_config_path", type=str, default=None)
    parser.add_argument("--serial_port", type=str, default=None)
    args = parser.parse_args()

    print("Initializing hardware interface...")
    try:
        duck_config = DuckConfig(config_json_path=args.duck_config_path)

        # Choose HWI implementation
        HWI_class = None
        if getattr(duck_config, "use_waveshare", False) and WaveshareHWI is not None:
            HWI_class = WaveshareHWI
        else:
            HWI_class = RustypotHWI

        if HWI_class is None:
            raise RuntimeError("No suitable HWI implementation found (rustypot or waveshare)")

        if args.serial_port is not None:
            hwi = HWI_class(duck_config, args.serial_port)
        else:
            hwi = HWI_class(duck_config)

        print("Successfully connected to hardware!")
    except Exception as e:
        print(f"Error connecting to hardware: {e}")
        print(f"Error details: {traceback.format_exc()}")
        print("Check that the robot is powered on and connection parameters are correct.")
        return

    # Try to enable torque globally if supported
    print("\nTurning on motors (best-effort)...")
    unresponsive_motors = []
    try:
        if hasattr(hwi, "turn_on"):
            hwi.turn_on()
        elif hasattr(hwi, "io") and hasattr(hwi.io, "enable_torque"):
            # rustypot-like API
            for jname, jid in hwi.joints.items():
                try:
                    hwi.io.enable_torque([jid])
                except Exception:
                    pass
    except Exception:
        pass

    # Per-motor low-torque attempt (best-effort)
    for joint_name, joint_id in hwi.joints.items():
        try:
            print(f"Setting low torque for motor '{joint_name}' (ID: {joint_id})...")
            if hasattr(hwi, "set_kps"):
                # WaveshareHWI compatibility
                hwi.set_kps([30] * len(hwi.joints))
                print(f"✓ Low torque (kps) set for '{joint_name}'")
            elif hasattr(hwi, "io") and hasattr(hwi.io, "set_kps"):
                hwi.io.set_kps([joint_id], [10])
                print(f"✓ Low torque set successfully for motor '{joint_name}' (ID: {joint_id}).")
        except Exception as e:
            print(f"✗ Error setting low torque for motor '{joint_name}' (ID: {joint_id}): {e}")
            print(f"Error details: {traceback.format_exc()}")
            unresponsive_motors.append((joint_name, joint_id))
    
    # Check if all motors are responsive
    print("\nChecking if all motors are responsive...")
    
    for joint_name, joint_id in hwi.joints.items():
        # Skip motors that already failed
        if (joint_name, joint_id) in unresponsive_motors:
            print(f"Skipping previously unresponsive motor: '{joint_name}' (ID: {joint_id})")
            continue

        print(f"Attempting to read position from motor '{joint_name}' (ID: {joint_id})...")
        try:
            # Try to read the position to check if motor is responsive
            pos_val = None
            # Waveshare packet
            if hasattr(hwi, "packet"):
                try:
                    p, _, _ = hwi.packet.ReadPos(joint_id)
                    pos_val = p
                except Exception:
                    pos_val = None
            # HWI wrapper method
            if pos_val is None and hasattr(hwi, "get_present_positions"):
                try:
                    pos_list = hwi.get_present_positions()
                    keys = list(hwi.joints.keys())
                    idx = keys.index(joint_name)
                    pos_val = pos_list[idx]
                except Exception:
                    pos_val = None
            # rustypot io
            if pos_val is None and hasattr(hwi, "io") and hasattr(hwi.io, "read_present_position"):
                try:
                    pos_val = hwi.io.read_present_position([joint_id])[0]
                except Exception:
                    pos_val = None

            if pos_val is None:
                raise RuntimeError("Could not read position")

            print(f"✓ Motor '{joint_name}' (ID: {joint_id}) is responsive. Position: {pos_val}")
        except Exception as e:
            print(f"✗ Error accessing motor '{joint_name}' (ID: {joint_id}): {e}")
            print(f"Error details for motor {joint_id}: {traceback.format_exc()}")
            unresponsive_motors.append((joint_name, joint_id))
    
    if unresponsive_motors:
        print("\nWARNING: Some motors are not responsive!")
        print("Unresponsive motors:", unresponsive_motors)
        continue_anyway = input("Do you want to continue anyway? (y/n): ").lower()
        if continue_anyway != 'y':
            print("Exiting...")
            try:
                print("Attempting to turn off responsive motors before exiting...")
                for joint_name, joint_id in hwi.joints.items():
                    if (joint_name, joint_id) not in unresponsive_motors:
                        try:
                            if hasattr(hwi, "turn_off"):
                                hwi.turn_off()
                            elif hasattr(hwi, "io") and hasattr(hwi.io, "disable_torque"):
                                hwi.io.disable_torque([joint_id])
                            print(f"Disabled torque for motor '{joint_name}' (ID: {joint_id})")
                        except:
                            pass
            except:
                pass
            return

    # Test moving each motor individually
    print("\n--- Motor Movement Test ---")
    print("This will move each motor by a small amount to check if it's working correctly.")
    input("Press Enter to begin the movement test...")
    
    for joint_name, joint_id in hwi.joints.items():
        # Skip unresponsive motors
        if (joint_name, joint_id) in unresponsive_motors:
            print(f"Skipping unresponsive motor: '{joint_name}' (ID: {joint_id})")
            continue

        print(f"\nTesting motor: '{joint_name}' (ID: {joint_id})")
        test_this_motor = input(f"Test this motor? (Enter/y for yes, n to skip, q to quit): ").lower()
        
        if test_this_motor == 'q':
            print("Exiting movement test...")
            break
            
        if test_this_motor == 'n':
            print(f"Skipping '{joint_name}' (ID: {joint_id})")
            continue
        
        try:
            # Read current position (support multiple HWI types)
            print(f"Reading current position from motor '{joint_name}' (ID: {joint_id})...")
            if hasattr(hwi, "packet"):
                cur_count, _, _ = hwi.packet.ReadPos(joint_id)
                current_position = hwi.servo_pos_to_rad(cur_count) if hasattr(hwi, "servo_pos_to_rad") else cur_count
            elif hasattr(hwi, "get_present_positions"):
                plist = hwi.get_present_positions()
                keys = list(hwi.joints.keys())
                idx = keys.index(joint_name)
                current_position = plist[idx]
            elif hasattr(hwi, "io") and hasattr(hwi.io, "read_present_position"):
                current_position = hwi.io.read_present_position([joint_id])[0]
            else:
                raise RuntimeError("No method to read current position")

            print(f"Current position: {current_position}")

            # Decide target
            delta = 0.1
            if hasattr(hwi, "rad_to_servo_pos"):
                target_rad = current_position + delta
                target_count = hwi.rad_to_servo_pos(target_rad)
            else:
                target_count = current_position + delta

            # Command move
            print(f"Moving motor '{joint_name}' (ID: {joint_id}) to test position...")
            if hasattr(hwi, "packet"):
                hwi.packet.WritePos(joint_id, int(target_count), 300, 1000)
            elif hasattr(hwi, "io") and hasattr(hwi.io, "write_goal_position"):
                hwi.io.write_goal_position([joint_id], [target_count])
            else:
                raise RuntimeError("No method to command motor movement")

            time.sleep(1.0)

            # Read back
            if hasattr(hwi, "packet"):
                new_count, _, _ = hwi.packet.ReadPos(joint_id)
                new_position = hwi.servo_pos_to_rad(new_count) if hasattr(hwi, "servo_pos_to_rad") else new_count
            elif hasattr(hwi, "io") and hasattr(hwi.io, "read_present_position"):
                new_position = hwi.io.read_present_position([joint_id])[0]
            else:
                new_position = None

            print(f"New position: {new_position}")

            # Return
            print(f"Returning motor '{joint_name}' (ID: {joint_id}) to original position...")
            if hasattr(hwi, "packet") and hasattr(hwi, "rad_to_servo_pos"):
                orig_count = hwi.rad_to_servo_pos(current_position)
                hwi.packet.WritePos(joint_id, int(orig_count), 300, 1000)
            elif hasattr(hwi, "io") and hasattr(hwi.io, "write_goal_position"):
                hwi.io.write_goal_position([joint_id], [current_position])

            time.sleep(1.0)

            print(f"✓ Motor '{joint_name}' (ID: {joint_id}) movement test completed.")

        except Exception as e:
            print(f"Error testing motor '{joint_name}' (ID: {joint_id}): {e}")
            print(f"Error details: {traceback.format_exc()}")
    
    # Turn off motors
    print("\nTurning off motors one by one...")
    for joint_name, joint_id in hwi.joints.items():
        if (joint_name, joint_id) in unresponsive_motors:
            print(f"Skipping turning off unresponsive motor: '{joint_name}' (ID: {joint_id})")
            continue
            
        try:
            print(f"Disabling torque for motor '{joint_name}' (ID: {joint_id})...")
            hwi.io.disable_torque([joint_id])
            print(f"✓ Motor '{joint_name}' (ID: {joint_id}) turned off successfully.")
        except Exception as e:
            print(f"✗ Error turning off motor '{joint_name}' (ID: {joint_id}): {e}")
            print(f"Error details: {traceback.format_exc()}")
    
    print("\nMotor test completed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Attempting to turn off motors...")
        try:
            # try to use existing hwi if present
            if 'hwi' in globals():
                hw = globals()['hwi']
            else:
                # fallback: try to create one from default config
                cfg = DuckConfig()
                if getattr(cfg, "use_waveshare", False) and WaveshareHWI is not None:
                    hw = WaveshareHWI(cfg)
                elif RustypotHWI is not None:
                    hw = RustypotHWI(cfg)
                else:
                    hw = None

            if hw is not None:
                for joint_name, joint_id in hw.joints.items():
                    try:
                        if hasattr(hw, "turn_off"):
                            hw.turn_off()
                        elif hasattr(hw, "io") and hasattr(hw.io, "disable_torque"):
                            hw.io.disable_torque([joint_id])
                        print(f"✓ Motor '{joint_name}' (ID: {joint_id}) turned off successfully.")
                    except Exception as e:
                        print(f"✗ Error turning off motor '{joint_name}' (ID: {joint_id}): {e}")
        except Exception as e:
            print(f"Error initializing HWI to turn off motors: {e}")
            print(f"Error details: {traceback.format_exc()}")