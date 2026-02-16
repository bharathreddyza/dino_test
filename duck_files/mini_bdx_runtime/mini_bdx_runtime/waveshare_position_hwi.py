"""
Waveshare Serial Bus Servo Hardware Interface for Open Duck Mini
Replaces rustypot_position_hwi.py for use with Waveshare ST servos

Supports:
- SC-15 Servo (Protocol ST)
- SC servo series with protocol_packet_handler

Key differences from Feetech:
- Uses PortHandler + sms_sts protocol stack instead of rustypot
- Position values in 0-2048 range (instead of radians internally converted)
- Speed commands via WritePosEx method
"""

import time
import numpy as np
from mini_bdx_runtime.duck_config import DuckConfig

# Import Waveshare SDK - adjust path as needed based on your setup
import sys
import os

# Add path to Waveshare SDK
# Adjust this path to match your installation
SDK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "STServo_Python", "stservo-env", "scservo_sdk")
if os.path.exists(SDK_PATH):
    sys.path.insert(0, SDK_PATH)

try:
    from scservo_sdk import PortHandler, sms_sts
    from scservo_sdk.scservo_def import COMM_SUCCESS
except ImportError:
    print("WARNING: Could not import scservo_sdk. Make sure Waveshare SDK is in Python path.")
    PortHandler = None
    sms_sts = None
    COMM_SUCCESS = 0


class WaveshareHWI:
    """
    Hardware Interface for Waveshare ST servo series
    
    This class provides the same interface as rustypot_position_hwi.HWI
    but uses the Waveshare scservo_sdk instead.
    """
    
    # Servo position range: 0-2048 represents 0-360 degrees
    # 1 unit = 360/2048 = 0.176 degrees = 3.07 millidegrees
    SERVO_POS_RANGE = 2048
    SERVO_DEG_RANGE = 360.0
    
    def __init__(self, duck_config: DuckConfig, usb_port: str = "/dev/ttyACM0"):
        """
        Initialize Waveshare hardware interface
        
        Args:
            duck_config: DuckConfig object with joint offsets
            usb_port: Serial port name (e.g., "COM5" on Windows, "/dev/ttyACM0" on Linux)
        """
        self.duck_config = duck_config
        self.usb_port = usb_port
        
        # Joint mapping: joint_name -> servo_id
        self.joints = {
            "left_hip_yaw": 20,
            "left_hip_roll": 21,
            "left_hip_pitch": 22,
            "left_knee": 23,
            "left_ankle": 24,
            "neck_pitch": 30,
            "head_pitch": 31,
            "head_yaw": 32,
            "head_roll": 33,
            "right_hip_yaw": 10,
            "right_hip_roll": 11,
            "right_hip_pitch": 12,
            "right_knee": 13,
            "right_ankle": 14,
        }
        
        # Zero position in radians (for consistency with other code)
        self.zero_pos = {joint: 0.0 for joint in self.joints}
        
        # Initial/home position in radians
        self.init_pos = {
            "left_hip_yaw": 0.002,
            "left_hip_roll": 0.053,
            "left_hip_pitch": -0.63,
            "left_knee": 1.368,
            "left_ankle": -0.784,
            "neck_pitch": 0.0,
            "head_pitch": 0.0,
            "head_yaw": 0,
            "head_roll": 0,
            "right_hip_yaw": -0.003,
            "right_hip_roll": -0.065,
            "right_hip_pitch": 0.635,
            "right_knee": 1.379,
            "right_ankle": -0.796,
        }
        
        # Load joint offsets from duck config
        self.joints_offsets = self.duck_config.joints_offset
        
        # PID gains for each servo (14 DoF)
        self.kps = np.ones(len(self.joints)) * 32  # default KP
        self.kds = np.ones(len(self.joints)) * 0   # default KD
        self.low_torque_kps = np.ones(len(self.joints)) * 2
        
        # Initialize serial communication
        if PortHandler is None or sms_sts is None:
            raise RuntimeError("Waveshare SDK not available. Check SDK path and imports.")
        
        self.port_handler = PortHandler(usb_port)
        self.packet_handler = sms_sts(self.port_handler)
        
        # Open port and set baud rate
        if not self.port_handler.openPort():
            raise RuntimeError(f"Failed to open serial port {usb_port}")
        
        # Set baud rate to 1Mbps (0 = 1000000 bps for SMS_STS series)
        if not self.port_handler.setBaudRate(1000000):
            raise RuntimeError("Failed to set baud rate")
        
        print(f"✓ Serial port {usb_port} opened successfully")
    
    def rad_to_servo_pos(self, rad):
        """
        Convert radians to servo position value (0-2048)
        
        Assumes servo 0-position corresponds to 0 radians
        and full rotation (±π or 2π based on servo mount) maps to position range
        """
        # This conversion depends on your mechanical setup
        # Adjust the formula based on your servo's mechanical limits
        # Example: assume ±π radians maps to 0-2048
        servo_pos = (rad / np.pi) * (self.SERVO_POS_RANGE / 2) + (self.SERVO_POS_RANGE / 2)
        return np.clip(servo_pos, 0, 2047)
    
    def servo_pos_to_rad(self, servo_pos):
        """
        Convert servo position value (0-2048) to radians
        
        Inverse of rad_to_servo_pos
        """
        # Inverse conversion
        rad = ((servo_pos - self.SERVO_POS_RANGE / 2) / (self.SERVO_POS_RANGE / 2)) * np.pi
        return rad
    
    def set_kps(self, kps):
        """
        Set KP (proportional gain) for all servos
        
        Args:
            kps: List of KP values (length = number of joints)
        """
        self.kps = np.array(kps)
        # Note: Waveshare servos use different register for P gain
        # You may need to implement this based on your servo's protocol
        # For now, this is a placeholder
        print(f"KP values set to: {kps}")
    
    def set_kds(self, kds):
        """
        Set KD (derivative gain) for all servos
        
        Args:
            kds: List of KD values (length = number of joints)
        """
        self.kds = np.array(kds)
        # Note: Waveshare servos use different register for D gain
        print(f"KD values set to: {kds}")
    
    def set_kp(self, servo_id, kp):
        """
        Set KP for a single servo
        
        Args:
            servo_id: Servo ID
            kp: KP value
        """
        # Implement single servo KP setting if needed
        print(f"KP for servo {servo_id} set to: {kp}")
    
    def turn_on(self):
        """
        Power on servos and move to initial position
        
        Sequence:
        1. Enable torque with low KP
        2. Move to init_pos
        3. Set high KP for stiff walking
        4. Wait for servos to settle
        """
        print("Turning on servos...")
        
        # Step 1: Enable low torque mode
        self.set_kps(self.low_torque_kps)
        print("  - Low KP set")
        time.sleep(0.5)
        
        # Step 2: Move to initial positions
        self.set_position_all(self.init_pos)
        print("  - Initial positions sent")
        time.sleep(2.5)  # Wait for servos to reach position
        
        # Step 3: Set high KP for operation
        self.set_kps(self.kps)
        print("  - High KP set")
        time.sleep(0.5)
        
        print("✓ Servos powered on and ready")
    
    def turn_off(self):
        """
        Disable torque on all servos
        """
        print("Turning off servos...")
        servo_ids = list(self.joints.values())
        for servo_id in servo_ids:
            # Write 0 to TORQUE_ENABLE (register varies by protocol)
            # This is a placeholder - adjust based on your servo protocol
            try:
                self.packet_handler.write1ByteTxRx(servo_id, 40, 0)  # 40 is SMS_STS_TORQUE_ENABLE
            except:
                pass
        print("✓ Servos powered off")
    
    def set_position(self, joint_name, pos):
        """
        Set position for a single joint (in radians)
        
        Args:
            joint_name: Name of the joint
            pos: Position in radians
        """
        servo_id = self.joints[joint_name]
        
        # Apply offset
        pos_with_offset = pos + self.joints_offsets[joint_name]
        
        # Convert to servo position
        servo_pos = int(self.rad_to_servo_pos(pos_with_offset))
        
        # Send command
        # WritePosEx(id, position, speed, acceleration)
        # Speed: command speed (0-3000, higher = faster)
        # Acceleration: command acceleration (0-254)
        try:
            speed = 500  # Default speed
            acceleration = 30  # Default acceleration
            self.packet_handler.WritePosEx(servo_id, servo_pos, speed, acceleration)
        except Exception as e:
            print(f"Error setting position for {joint_name}: {e}")
    
    def set_position_all(self, joints_positions):
        """
        Set positions for all joints simultaneously
        
        Args:
            joints_positions: Dict with joint names as keys and positions (radians) as values
        """
        for joint_name, position in joints_positions.items():
            # Skip if joint not in mapping
            if joint_name not in self.joints:
                continue
            
            servo_id = self.joints[joint_name]
            
            # Apply offset
            pos_with_offset = position + self.joints_offsets[joint_name]
            
            # Convert to servo position
            servo_pos = int(self.rad_to_servo_pos(pos_with_offset))
            
            try:
                speed = 500  # Default speed
                acceleration = 30  # Default acceleration
                self.packet_handler.WritePosEx(servo_id, servo_pos, speed, acceleration)
            except Exception as e:
                print(f"Error setting position for {joint_name}: {e}")
    
    def get_present_positions(self, ignore=[]):
        """
        Read present positions from all servos
        
        Args:
            ignore: List of joint names to ignore
            
        Returns:
            NumPy array of positions in radians for non-ignored joints
        """
        present_positions = []
        
        for joint_name in self.joints.keys():
            # Skip ignored joints
            if joint_name in ignore:
                continue
            
            servo_id = self.joints[joint_name]
            
            try:
                # ReadPos returns (position, comm_result, error)
                servo_pos, comm_result, error = self.packet_handler.ReadPos(servo_id)
                
                if comm_result != COMM_SUCCESS:
                    print(f"Error reading position from {joint_name}: comm_result={comm_result}")
                    return None
                
                # Convert servo position to radians
                rad_value = self.servo_pos_to_rad(servo_pos)
                
                # Remove offset
                rad_value = rad_value - self.joints_offsets[joint_name]
                
                present_positions.append(rad_value)
            except Exception as e:
                print(f"Exception reading position from {joint_name}: {e}")
                return None
        
        return np.array(np.around(present_positions, 3))
    
    def get_present_velocities(self, rad_s=True, ignore=[]):
        """
        Read present velocities from all servos
        
        Args:
            rad_s: If True, return rad/s; if False, return rev/min
            ignore: List of joint names to ignore
            
        Returns:
            NumPy array of velocities
        """
        present_velocities = []
        
        for joint_name in self.joints.keys():
            # Skip ignored joints
            if joint_name in ignore:
                continue
            
            servo_id = self.joints[joint_name]
            
            try:
                # ReadSpeed returns (speed, comm_result, error)
                servo_speed, comm_result, error = self.packet_handler.ReadSpeed(servo_id)
                
                if comm_result != COMM_SUCCESS:
                    print(f"Error reading speed from {joint_name}: comm_result={comm_result}")
                    return None
                
                # Speed is in units of rev/min or needs conversion
                # Waveshare servos typically return speed in a specific format
                # Convert to rad/s if requested
                if rad_s:
                    # Adjust conversion factor based on your servo specs
                    # This is an example - check your servo datasheet
                    velocity = servo_speed * 0.05  # Placeholder conversion
                else:
                    velocity = servo_speed
                
                present_velocities.append(velocity)
            except Exception as e:
                print(f"Exception reading velocity from {joint_name}: {e}")
                return None
        
        return np.array(np.around(present_velocities, 3))
    
    def read_voltage(self, servo_id):
        """
        Read voltage from a servo
        
        Args:
            servo_id: Servo ID
            
        Returns:
            Voltage in volts
        """
        try:
            voltage, comm_result, error = self.packet_handler.read1ByteTxRx(
                servo_id, 62  # SMS_STS_PRESENT_VOLTAGE register
            )
            # Waveshare returns voltage as raw value, convert if needed
            return voltage / 10.0  # Assuming 0.1V per unit
        except:
            return None
    
    def read_temperature(self, servo_id):
        """
        Read temperature from a servo
        
        Args:
            servo_id: Servo ID
            
        Returns:
            Temperature in Celsius
        """
        try:
            temp, comm_result, error = self.packet_handler.read1ByteTxRx(
                servo_id, 63  # SMS_STS_PRESENT_TEMPERATURE register
            )
            return temp
        except:
            return None
    
    def scan_servos(self, servo_range=range(1, 250)):
        """
        Scan for connected servos on the bus
        
        Args:
            servo_range: Range of IDs to scan
            
        Returns:
            List of detected servo IDs
        """
        detected_ids = []
        print("Scanning for servos...")
        
        for servo_id in servo_range:
            try:
                pos, comm_result, error = self.packet_handler.ReadPos(servo_id)
                if comm_result == COMM_SUCCESS:
                    detected_ids.append(servo_id)
                    print(f"  ✓ Found servo at ID {servo_id}")
            except:
                pass
        
        return detected_ids
    
    def close(self):
        """
        Close serial connection
        """
        if self.port_handler:
            self.port_handler.closePort()
            print("✓ Serial port closed")
