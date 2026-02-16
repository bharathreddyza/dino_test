# Waveshare Servo Integration - Setup & Testing Guide

## Quick Start Checklist

- [ ] Install Waveshare SDK (if not already done)
- [ ] Update Python path in `waveshare_position_hwi.py`
- [ ] Run servo discovery/ping test
- [ ] Calibrate position mapping for each joint
- [ ] Test servo movement without RL policy
- [ ] Run full RL policy

---

## Step 1: Setup Python Environment

### Option A: Using existing STServo_Python environment

If your `STServo_Python` folder already has the SDK:

```bash
cd Open_Duck_Mini_Runtime
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install Open Duck Mini dependencies
pip install -r mini_bdx_runtime/requirements.txt  # if exists
pip install numpy onnxruntime
```

### Option B: Add Waveshare SDK to Python path

Ensure `waveshare_position_hwi.py` can find the SDK:

```python
# In waveshare_position_hwi.py, line ~24-28:
SDK_PATH = os.path.join(
    os.path.dirname(__file__), 
    "..", "..", "..", 
    "STServo_Python", 
    "stservo-env", 
    "scservo_sdk"
)
if os.path.exists(SDK_PATH):
    sys.path.insert(0, SDK_PATH)
```

**Or** set PYTHONPATH environment variable:
```bash
# Linux/Mac
export PYTHONPATH="${PYTHONPATH}:/path/to/STServo_Python/stservo-env"

# Windows (PowerShell)
$env:PYTHONPATH = "C:\path\to\STServo_Python\stservo-env"
```

---

## Step 2: Identify Serial Port & Servo IDs

### Find Serial Port

**Windows**:
```powershell
# Open Device Manager or use Python
python -c "import serial; print([p.device for p in serial.tools.list_ports.comports()])"
# Output: ['COM5', 'COM3', ...]
```

**Linux**:
```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Output: /dev/ttyACM0
```

### Discover Servo IDs

Create a test script:

```python
# test_servo_discovery.py
import sys
sys.path.insert(0, "path/to/STServo_Python/stservo-env")

from scservo_sdk import PortHandler, sms_sts

PORT = "COM5"  # Change to your port
BAUDRATE = 1000000

port = PortHandler(PORT)
if not port.openPort():
    print(f"Failed to open {PORT}")
    exit(1)

if not port.setBaudRate(BAUDRATE):
    print("Failed to set baud rate")
    exit(1)

packet_handler = sms_sts(port)

print("Scanning for servos...")
found = []

for servo_id in range(0, 254):
    try:
        pos, comm_result, error = packet_handler.ReadPos(servo_id)
        if comm_result == 0:  # COMM_SUCCESS
            found.append(servo_id)
            print(f"  ✓ Servo ID {servo_id}: position={pos}")
    except:
        pass

print(f"\nFound {len(found)} servos: {found}")
port.closePort()
```

Run it:
```bash
python test_servo_discovery.py
```

Expected output:
```
Scanning for servos...
  ✓ Servo ID 10: position=1024
  ✓ Servo ID 11: position=1024
  ✓ Servo ID 12: position=1024
  ...
Found 14 servos: [10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33]
```

---

## Step 3: Calibrate Position Mapping

The crucial step: creating the `rad_to_servo_pos()` function.

### Manual Calibration Process

1. **Move a servo to known positions and record the values**:

```python
# test_calibration.py
import sys
sys.path.insert(0, "path/to/STServo_Python/stservo-env")
from scservo_sdk import PortHandler, sms_sts
import time

PORT = "COM5"
SERVO_ID = 10  # right_hip_yaw - start with a leg servo

port = PortHandler(PORT)
port.openPort()
port.setBaudRate(1000000)
packet_handler = sms_sts(port)

print(f"Calibrating Servo ID {SERVO_ID}...")
print("Position mapping across full range:\n")
print("Position | Degrees")
print("-" * 20)

test_positions = [0, 256, 512, 768, 1024, 1280, 1536, 1792, 2047]
measurements = []

for pos in test_positions:
    # Move servo to position
    packet_handler.WritePosEx(SERVO_ID, pos, 500, 30)
    time.sleep(0.5)
    
    # Read back position
    read_pos, comm_result, error = packet_handler.ReadPos(SERVO_ID)
    
    # Calculate degrees (assuming linear mapping 0-2048 = 0-360°)
    degrees = (pos / 2048.0) * 360.0
    
    print(f"{pos:4d}    | {degrees:6.1f}°")
    measurements.append((pos, degrees))

port.closePort()

# From this output, you can create accurate mapping functions
# For example, if you mounted the servo with reverse direction:
# degrees = 360 - (pos / 2048) * 360
```

2. **Calculate conversion formulas**:

Once you know the mechanical mapping, update `waveshare_position_hwi.py`:

```python
def rad_to_servo_pos(self, rad):
    """
    Convert radians to servo position (0-2048)
    
    MUST BE CALIBRATED FOR YOUR SPECIFIC SERVO MOUNTS
    
    Example calibration result:
    - Servo at rest: 0 rad = 1024 (center)
    - ±π radians = ±1024 units
    """
    # Default assumption (linear, centered at 1024):
    servo_pos = (rad / np.pi) * (1024) + 1024
    
    # If servo is reversed:
    # servo_pos = 1024 - (rad / np.pi) * 1024
    
    # Clamp to valid range
    return np.clip(servo_pos, 0, 2047)

def servo_pos_to_rad(self, servo_pos):
    """Inverse of rad_to_servo_pos"""
    rad = ((servo_pos - 1024) / 1024.0) * np.pi
    return rad
```

---

## Step 4: Verify Servo Response

### Test 1: Center Position

```python
# test_center.py
from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI
from mini_bdx_runtime.duck_config import DuckConfig

config = DuckConfig("path/to/duck_config.json")
hwi = WaveshareHWI(config, serial_port="COM5")

# Read initial positions
pos = hwi.get_present_positions()
print(f"Current positions (rad): {pos}")

# Move all servos to init position
print("Moving to init position...")
hwi.set_position_all(hwi.init_pos)

time.sleep(2)

# Verify positions
pos = hwi.get_present_positions()
print(f"Final positions (rad): {pos}")

hwi.close()
```

### Test 2: Smooth Movement

```python
# test_smooth_movement.py
import numpy as np
import time

hwi = WaveshareHWI(config, serial_port="COM5")

# Wave each leg back and forth
test_positions = hwi.init_pos.copy()

for step in range(20):  # 20 back-and-forth cycles
    # Move left leg up
    test_positions["left_hip_pitch"] = hwi.init_pos["left_hip_pitch"] + 0.3
    hwi.set_position_all(test_positions)
    time.sleep(0.5)
    
    # Move left leg down
    test_positions["left_hip_pitch"] = hwi.init_pos["left_hip_pitch"] - 0.3
    hwi.set_position_all(test_positions)
    time.sleep(0.5)

hwi.close()
```

---

## Step 5: Integration with RL Policy

### Modify v2_rl_walk_mujoco.py

**Change Line 6**:
```python
# OLD:
from mini_bdx_runtime.rustypot_position_hwi import HWI

# NEW:
from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI as HWI
```

### Test with Real Policy

```python
# Run the full policy
python scripts/v2_rl_walk_mujoco.py \
    --onnx_model_path="/path/to/policy.onnx" \
    --duck_config_path="/path/to/duck_config.json" \
    --control_freq=50 \
    -p 30 \
    -d 0
```

**Monitor output** for:
- Servo response (should move smoothly)
- Observation vector (should print without errors)
- Frame rate (target: 50 Hz)

---

## Step 6: Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'scservo_sdk'"

**Solution**:
1. Check SDK path in `waveshare_position_hwi.py` line 24-28
2. Verify files exist: `ls stservo-env/scservo_sdk/`
3. Set PYTHONPATH explicitly

```bash
export PYTHONPATH="$PWD/path/to/stservo-env:$PYTHONPATH"
python test_discovery.py
```

### Problem: "Failed to open serial port"

**Solution**:
1. Verify port name with device manager or `ls /dev/ttyACM*`
2. Check USB cable connection
3. Try different baud rates (default: 1000000)
4. Check permissions (Linux): `sudo usermod -a -G dialout $USER`

### Problem: "Servo not responding / COMM_TIMEOUT"

**Solution**:
1. Verify servo ID is correct
2. Check servo power (should be 5-8V)
3. Check serial bus connections (A, B, GND)
4. Reduce baud rate temporarily for testing

### Problem: Servos move to wrong positions

**Solution**:
1. Recalibrate `rad_to_servo_pos()` conversion
2. Check offset values in duck_config.json
3. Verify servo mechanical mounting (not reversed)
4. Print intermediate values:
   ```python
   print(f"Goal rad: {rad}, servo_pos: {servo_pos}")
   ```

### Problem: Policy outputs zeros / robot doesn't move

**Solution**:
1. Check observation vector length (must be exactly 125)
2. Print obs in `get_obs()`: `print(f"Obs shape: {obs.shape}, sum: {np.sum(obs)}")`
3. Verify all sensors return valid values (not NaN)
4. Check policy file path and ONNX format

---

## Step 7: Performance Tuning

### Speed & Acceleration

In `waveshare_position_hwi.py`, `set_position_all()` method:

```python
speed = 500        # 0-3000 (higher = faster)
acceleration = 30  # 0-254 (higher = faster)
```

**Adjust if**:
- Robot too slow: increase both values
- Robot jerky/unstable: decrease acceleration
- Observation lag: increase speed

### Action Scale

In `v2_rl_walk_mujoco.py` initialization:

```python
action_scale=0.25  # Multiply policy output by this

# Try:
# 0.1 = cautious (jerky, less power)
# 0.25 = default (smooth, good power)
# 0.5 = aggressive (faster, may be unstable)
```

### Control Frequency

Default 50 Hz is standard. Only change if:
- Hardware can't keep up: reduce to 30 Hz
- Smoother control needed: try 100 Hz (if hardware supports)

```python
python scripts/v2_rl_walk_mujoco.py \
    --control_freq=30 \  # Slower
    ...
```

---

## Reference: Complete Joint Configuration

From `waveshare_position_hwi.py`:

```python
self.joints = {
    "left_hip_yaw": 20,      # Servo ID 20
    "left_hip_roll": 21,     # Servo ID 21
    "left_hip_pitch": 22,    # Servo ID 22
    "left_knee": 23,         # Servo ID 23
    "left_ankle": 24,        # Servo ID 24
    "neck_pitch": 30,        # Servo ID 30
    "head_pitch": 31,        # Servo ID 31
    "head_yaw": 32,          # Servo ID 32
    "head_roll": 33,         # Servo ID 33
    "right_hip_yaw": 10,     # Servo ID 10
    "right_hip_roll": 11,    # Servo ID 11
    "right_hip_pitch": 12,   # Servo ID 12
    "right_knee": 13,        # Servo ID 13
    "right_ankle": 14,       # Servo ID 14
}

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
```

---

## Final Validation

Once integrated, you should see:

```
✓ Serial port COM5 opened successfully
✓ Servos powered on and ready
Starting
[Output from RL policy loop...]
Done parsing args
Done instantiating RLWalk
Starting
[Servo movement, gamepad commands, etc.]
```

If all is working, your Open Duck Mini can now walk with Waveshare servos!

---

## Contact & Debug

If issues persist:
1. Check your servo datasheet for register addresses
2. Verify communication with basic WritePosEx/ReadPos commands
3. Print intermediate values (position conversions, observations)
4. Compare with Feetech reference implementation

