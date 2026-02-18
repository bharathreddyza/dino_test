# Open Duck Mini RL Policy Architecture & Waveshare Servo Adaptation Guide

## Overview

The Open Duck Mini robot uses a **Reinforcement Learning (RL) policy** to control walking and movement. The policy is a neural network (ONNX format) that takes sensor observations as input and outputs motor target positions.

This document explains:
1. How the RL policy works with servos
2. Key components in the software architecture
3. How to adapt it for Waveshare servos instead of Feetech

---

## Part 1: RL Policy Control Flow

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RLWalk Main Loop (50Hz)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Sensor Input Collection                                      │
│     ├─ IMU (gyro, accel) -> raw_imu.py                          │
│     ├─ Joint positions (radians) -> HWI.get_present_positions() │
│     ├─ Joint velocities (rad/s) -> HWI.get_present_velocities() │
│     └─ Gamepad commands -> xbox_controller.py                   │
│                                                                  │
│  2. Observation Vector Assembly (get_obs)                        │
│     └─ Concatenate ALL sensor data in specific order            │
│        [gyro(3), accel(3), gamepad(7), pos(14), vel(14),        │
│         last_action(14), last_last_action(14),                  │
│         last_last_last_action(14), targets(14), contacts(4),    │
│         phase(2)] = 125-dim vector                              │
│                                                                  │
│  3. RL Policy Inference (ONNX)                                   │
│     └─ policy.infer(obs) -> action[14] (normalized actions)     │
│        Executes the trained neural network on observation       │
│                                                                  │
│  4. Action Post-Processing                                       │
│     ├─ action_scale: multiply by 0.25 (or other factor)         │
│     ├─ Convert to target positions: init_pos + action*scale     │
│     ├─ Optional: Low-pass filter for smoothing                  │
│     └─ Add head tracking (gamepad commands overlay)             │
│                                                                  │
│  5. Servo Command                                                │
│     └─ HWI.set_position_all(joint_dict) sends commands to all   │
│        14 servos via serial bus (WritePosEx)                    │
│                                                                  │
│  6. Control Loop Timing (target: 50 Hz)                          │
│     └─ Sleep to maintain 20ms cycle time (1/50Hz)               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| **Main Loop** | `scripts/v2_rl_walk_mujoco.py` | RLWalk class, control loop |
| **Hardware Interface** | `mini_bdx_runtime/rustypot_position_hwi.py` | Servo communication |
| **Policy Inference** | `mini_bdx_runtime/onnx_infer.py` | ONNX model execution |
| **Observation Assembly** | `RLWalk.get_obs()` | Sensor data collection |
| **Action Processing** | `mini_bdx_runtime/rl_utils.py` | Coordinate transformations |
| **IMU** | `mini_bdx_runtime/raw_imu.py` | Accelerometer + gyroscope |
| **Gamepad** | `mini_bdx_runtime/xbox_controller.py` | Remote control input |

---

## Part 2: Data Flow - From Sensors to Motors

### 2.1 Observation Vector Assembly (125 dimensions)

The policy requires observations in a **very specific order**:

```python
def get_obs(self):
    imu_data = self.imu.get_data()                    # [gyro_x, gyro_y, gyro_z, accel_x, accel_y, accel_z]
    dof_pos = self.hwi.get_present_positions(...)     # [14] joint positions in radians
    dof_vel = self.hwi.get_present_velocities(...)    # [14] joint velocities in rad/s
    cmds = self.last_commands                          # [7] gamepad analog values
    feet_contacts = self.feet_contacts.get()          # [4] contact sensors (FL, FR, BL, BR)
    
    obs = np.concatenate([
        imu_data["gyro"],                     # [3] gyro
        imu_data["accelero"],                 # [3] accel
        cmds,                                 # [7] gamepad
        dof_pos - self.init_pos,              # [14] RELATIVE positions (residual)
        dof_vel * 0.05,                       # [14] velocity (scaled by 0.05)
        self.last_action,                     # [14] previous action
        self.last_last_action,                # [14] action from 2 steps ago
        self.last_last_last_action,           # [14] action from 3 steps ago
        self.motor_targets,                   # [14] computed targets
        feet_contacts,                        # [4] contact info
        self.imitation_phase,                 # [2] sin/cos of gait phase
    ])
    
    return obs  # Total: 125 dimensions
```

**CRITICAL**: The policy was trained on observations in this exact order. If you change the order or dimensions, the policy will fail.

### 2.2 Action Output (14 dimensions)

The policy outputs 14 continuous values:

```python
action = self.policy.infer(obs)  # shape: (14,), range: [-1, 1]

# Convert to motor target positions:
motor_targets = self.init_pos + action * self.action_scale
#              ^init pose  ^normalized  ^scaling factor (e.g., 0.25)

# Apply to all 14 joints:
self.hwi.set_position_all(motor_targets)
```

**Joint Order** (must match exactly):
```
[0] left_hip_yaw      [7] head_pitch
[1] left_hip_roll     [8] head_yaw
[2] left_hip_pitch    [9] head_roll
[3] left_knee         [10] right_hip_yaw
[4] left_ankle        [11] right_hip_roll
[5] neck_pitch        [12] right_hip_pitch
[6] head_pitch        [13] right_knee, right_ankle (combined or separate)
                      [14] right_ankle
```

### 2.3 Hardware Interface (HWI) - The Bridge Layer

The **HWI (Hardware Interface)** is the crucial abstraction that:
- Converts radians → servo commands
- Reads servo positions → converts to radians
- Handles offsets and calibration
- Manages PID gains (KP, KD)

**Current implementation**: `rustypot_position_hwi.py`
- Uses `rustypot` library (Python binding to Feetech servos)
- Calls `self.io.write_goal_position()` for commands
- Calls `self.io.read_present_position()` for feedback

---

## Part 3: Comparing Feetech vs Waveshare Protocol

### Feetech (Current - rustypot library)

```python
# Initialization
self.io = rustypot.feetech(port, baudrate)

# Commands
self.io.write_goal_position([id1, id2, ...], [pos1, pos2, ...])  # radians
self.io.set_kps([id1, ...], [kp1, ...])
self.io.set_kds([id1, ...], [kd1, ...])

# Reading
positions = self.io.read_present_position([id1, id2, ...])  # radians
velocities = self.io.read_present_velocity([id1, id2, ...]) # rad/s
```

**Advantages**: 
- Works directly in radians (human-friendly)
- Python wrapper abstracts protocol details
- Automatic scaling

---

### Waveshare (Target - scservo_sdk)

```python
# Initialization
port_handler = PortHandler(port)
packet_handler = sms_sts(port_handler)

# Commands
packet_handler.WritePosEx(servo_id, position, speed, acceleration)
# position is 0-2048, not radians

# Reading (one at a time)
pos, comm_result, error = packet_handler.ReadPos(servo_id)
# Returns position in 0-2048 range

speed, comm_result, error = packet_handler.ReadSpeed(servo_id)
# Returns speed in servo-native units
```

**Key Differences**:
| Aspect | Feetech | Waveshare |
|--------|---------|-----------|
| **Position Range** | -π to π (radians) | 0-2048 (raw units) |
| **Commands** | Batch (multiple at once) | Individual + batch sync write |
| **Learning Curve** | Easy (radians) | Medium (unit conversion needed) |
| **Library** | rustypot (high-level) | scservo_sdk (low-level) |

---

## Part 4: Implementing Waveshare Adapter

### Strategy

**Do NOT modify RLWalk.** Instead, create a **drop-in replacement** for the HWI class that:

1. Accepts the same method signatures as `rustypot_position_hwi.HWI`
2. Internally handles Waveshare protocol details
3. Converts between radians ↔ servo position units

### Implementation File

**Location**: `mini_bdx_runtime/waveshare_position_hwi.py`

**Key Methods to Implement**:

```python
class WaveshareHWI:
    def __init__(self, duck_config, usb_port):
        # Initialize PortHandler + sms_sts
        # Open serial connection
        # Set baud rate to 1Mbps
    
    def rad_to_servo_pos(self, rad):
        # Convert radians to 0-2048 range
        servo_pos = (rad / π) * (2048/2) + 1024
        return clamp(servo_pos, 0, 2047)
    
    def servo_pos_to_rad(self, servo_pos):
        # Inverse conversion
    
    def set_position_all(self, joints_dict):
        # {joint_name: position_in_radians}
        for joint_name, rad in joints_dict.items():
            servo_id = self.joints[joint_name]
            servo_pos = self.rad_to_servo_pos(rad + self.joints_offsets[joint_name])
            self.packet_handler.WritePosEx(servo_id, servo_pos, speed=500, acc=30)
    
    def get_present_positions(self, ignore=[]):
        # Read all servos, convert to radians
        # Return numpy array (same format as rustypot)
    
    def get_present_velocities(self, rad_s=True, ignore=[]):
        # Read all servos, convert to rad/s
        # Return numpy array
    
    def set_kps(self, kps_list), set_kds(self, kds_list):
        # Store for later (Waveshare registers differ)
    
    def turn_on(self):
        # Low torque → Move to init → High torque
    
    def turn_off(self):
        # Disable torque
```

---

## Part 5: Usage - Switching to Waveshare

### Step 1: Update the Import

**Current** (`v2_rl_walk_mujoco.py` line 6):
```python
from mini_bdx_runtime.rustypot_position_hwi import HWI
```

**Change to**:
```python
from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI as HWI
```

Or use a config flag:
```python
if USE_WAVESHARE:
    from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI as HWI
else:
    from mini_bdx_runtime.rustypot_position_hwi import HWI
```

### Step 2: Update Serial Port Parameter

The `RLWalk` class accepts `serial_port` parameter:

```python
rl_walk = RLWalk(
    onnx_model_path="path/to/model.onnx",
    serial_port="COM5",  # Windows: COM5, Linux: /dev/ttyACM0
    # ... other params
)
```

### Step 3: Run

```bash
python v2_rl_walk_mujoco.py \
    --onnx_model_path="policy.onnx" \
    --duck_config_path="duck_config.json"
```

---

## Part 6: Calibration & Tuning

### Position Mapping Calibration

The conversion from radians to servo units depends on your mechanical setup:

```python
def rad_to_servo_pos(self, rad, counts_per_pi=1024):
    # CUSTOMIZE BASED ON YOUR SERVO MOUNT
    # For Waveshare SC family (scscl) a common mapping is 1024 counts == π rad (180°).
    # For ST family (sms_sts) some firmwares use 2048 counts == π rad.
    # Use `counts_per_pi=1024` for SC, `2048` for ST.
    center = counts_per_pi // 2
    servo_pos = (rad / np.pi) * (counts_per_pi / 2) + center
    return np.clip(int(round(servo_pos)), 0, counts_per_pi - 1)
```

**You must calibrate this**:

1. Move each joint manually to known angles (e.g., 90°, 180°, 270°)
2. Read the servo position value
3. Calculate the mapping for your servo

Example calibration script:
```python
# Move servo ID 10 to center (should read ~1024)
packet_handler.WritePosEx(10, 1024, 500, 30)
pos, _, _ = packet_handler.ReadPos(10)
print(f"Position at center: {pos}")

# Compare with expected value from init_pos
```

### Speed & Acceleration Parameters

Adjust these in `set_position_all()`:

```python
speed = 500      # 0-3000, higher = faster
acceleration = 30  # 0-254, higher = faster
```

The policy expects smooth, continuous motion. If servos are too slow, the policy won't reach its targets in time.

### KP/KD Tuning

**Currently limited** because Waveshare registers differ from Feetech.

You may need to:
1. Find the KP register address in your servo datasheet
2. Implement `set_kps()`/`set_kds()` to write to those registers
3. Or rely on factory defaults if acceptable

Current values (from `v2_rl_walk_mujoco.py`):
```python
kps = [30] * 14        # For body
kps[5:9] = [8] * 4     # Lower for head (8)

kds = [0] * 14         # Usually no derivative term
```

---

## Part 7: Troubleshooting

### Issue: "No servo detected"

**Cause**: Serial connection failing or wrong port
**Fix**:
- Run servo scan: `waveshare_position_hwi.WaveshareHWI.scan_servos()`
- Verify port name: `COM5` (Windows) or `/dev/ttyACM0` (Linux)
- Check USB cable connection
- Check servo IDs match configuration

### Issue: Servos don't move smoothly / twitching

**Cause**: Position update rate too slow or observations misaligned
**Fix**:
- Increase speed parameter in `WritePosEx()`
- Reduce action_scale (e.g., 0.1 instead of 0.25)
- Check observation vector assembly (wrong order = policy fails)

### Issue: Policy inference produces zeros or NaNs

**Cause**: Observation dimensions mismatch
**Fix**:
- Verify `get_obs()` returns exactly 125 values
- Check joint count: must be 14 (excluding antennas)
- Ensure position/velocity arrays are not None

### Issue: Servo goes to weird positions

**Cause**: rad_to_servo_pos conversion wrong
**Fix**:
- Calibrate conversion function
- Print intermediate values: `print(f"rad={rad}, servo_pos={servo_pos}")`
- Test individual servos with known positions

---

## Part 8: Key Code Snippets for Reference

### Main Control Loop (simplified)

```python
class RLWalk:
    def run(self):
        while True:
            # 1. Read sensors
            obs = self.get_obs()
            
            # 2. Policy inference
            action = self.policy.infer(obs)
            
            # 3. Post-process
            motor_targets = self.init_pos + action * self.action_scale
            
            # 4. Send to servos
            self.hwi.set_position_all(motor_targets)
            
            # 5. Maintain 50 Hz
            time.sleep(0.02)
```

### Observation Assembly

```python
def get_obs(self):
    gyro = self.imu.get_data()["gyro"]                          # shape (3,)
    accel = self.imu.get_data()["accelero"]                     # shape (3,)
    pos = self.hwi.get_present_positions(ignore=[...])          # shape (14,)
    vel = self.hwi.get_present_velocities(ignore=[...])         # shape (14,)
    
    obs = np.concatenate([gyro, accel, gamepad, pos-init, 
                         vel*0.05, action, action_prev, action_prev2, 
                         targets, contacts, phase])
    
    return obs  # shape (125,)
```

---

## Summary

**To adapt Open Duck Mini for Waveshare servos**:

1. **Create** `waveshare_position_hwi.py` with `WaveshareHWI` class ✓ (provided)
2. **Implement** conversion functions (`rad_to_servo_pos`, `servo_pos_to_rad`)
3. **Calibrate** position mapping for your specific servo mounts
4. **Change import** in `v2_rl_walk_mujoco.py` to use `WaveshareHWI`
5. **Test** with servo scan, manual position commands, then full RL policy

The rest of the codebase (policy, RL loop, observation assembly) remains **unchanged**.

---

## References

- **Feetech SDK**: rustypot Python library
- **Waveshare SDK**: scservo_sdk (included in your STServo_Python folder)
- **Open Duck Mini**: Official documentation and source code
- **ONNX**: Model format used for policy inference

