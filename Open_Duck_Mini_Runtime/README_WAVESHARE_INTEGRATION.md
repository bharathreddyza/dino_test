# Waveshare Servo Adaptation - Complete Summary

## What You Have Now

I've created a complete adaptation package to use **Waveshare ST servos** with the **Open Duck Mini RL policy**. Here's what's included:

### Files Created

1. **`mini_bdx_runtime/waveshare_position_hwi.py`** (NEW)
   - Drop-in replacement for `rustypot_position_hwi.py`
   - Implements `WaveshareHWI` class with identical interface
   - Handles all conversions between radians (RLWalk) ↔ servo units (Waveshare)
   - **Ready to use** but needs position mapping calibration

2. **`WAVESHARE_ADAPTATION_GUIDE.md`** (NEW)
   - Complete technical documentation
   - Explains how RL policy operates
   - Data flow from sensors → policy → servos
   - Feetech vs Waveshare protocol comparison
   - Key code snippets and implementation details

3. **`SETUP_TESTING_GUIDE.md`** (NEW)
   - Step-by-step setup instructions
   - Servo discovery and calibration procedures
   - Testing scripts and validation steps
   - Troubleshooting guide

4. **`COMPARISON_MIGRATION_REFERENCE.md`** (NEW)
   - Architecture diagrams and flowcharts
   - Side-by-side method mappings
   - Unit conversion formulas
   - Migration checklist
   - Quick reference table

5. **`test_waveshare_setup.py`** (NEW)
   - Automated diagnostic test suite
   - Tests: discovery, position reading, movement, HWI integration
   - Usage: `python test_waveshare_setup.py --port COM5 --test all`

---

## How It Works - 30 Second Overview

### The RL Policy Loop (50 Hz)

```
while True:
    obs = get_obs()                    # Collect sensor data (125 values)
    action = policy.infer(obs)         # Run neural network
    target_pos = init_pos + action*0.25   # Convert to radian targets
    hwi.set_position_all(target_pos)   # Send to servos
    time.sleep(0.02)                   # Control at 50 Hz
```

### Hardware Abstraction (The Bridge)

**Open Duck Mini** expects:
- Positions in **radians** (e.g., -0.63 rad)
- Methods like `hwi.set_position_all(dict)`

**Waveshare servos** provide:
- Positions in **raw units** (0-2048)
- Methods like `WritePosEx(servo_id, position, speed, acc)`

**WaveshareHWI** converts between them:
```python
# Receives radians from RLWalk
servo_pos = rad_to_servo_pos(radian_value)  # Converts to 0-2048

# Sends to Waveshare
packet_handler.WritePosEx(servo_id, servo_pos, speed, acc)

# Later, reads from Waveshare
servo_pos = packet_handler.ReadPos(servo_id)  # Gets 0-2048
radian_value = servo_pos_to_rad(servo_pos)    # Converts to radians

# Returns to RLWalk
return radian_array
```

---

## Quick Start (5 Minutes)

### 1. Copy the HWI file
```bash
cp waveshare_position_hwi.py mini_bdx_runtime/mini_bdx_runtime/
```

### 2. Update the import in `scripts/v2_rl_walk_mujoco.py`
```python
# Line 6 - CHANGE FROM:
from mini_bdx_runtime.rustypot_position_hwi import HWI

# TO:
from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI as HWI
```

### 3. Test servo connection
```bash
python test_waveshare_setup.py --port COM5 --test discovery
```

### 4. Calibrate position mapping (CRITICAL!)
Edit `waveshare_position_hwi.py`, method `rad_to_servo_pos()`:
```python
def rad_to_servo_pos(self, rad):
    # Modify this formula based on your servo mounts
    # Current: assumes ±π maps to 0-2048 (centered at 1024)
    servo_pos = (rad / np.pi) * 1024 + 1024
    return np.clip(servo_pos, 0, 2047)
```

### 5. Run the full policy
```bash
python scripts/v2_rl_walk_mujoco.py \
    --onnx_model_path="path/to/policy.onnx" \
    --duck_config_path="path/to/duck_config.json"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│            Your Open Duck Mini Robot                    │
│  (all code UNCHANGED except HWI class)                  │
└─────────────────────────────────┬───────────────────────┘
                                  │
                ┌─────────────────┴─────────────────┐
                │                                   │
                ▼                                   ▼
        ┌──────────────────┐            ┌──────────────────┐
        │  RLWalk Policy   │            │  RLWalk Policy   │
        │  Main Loop       │            │  (unchanged)     │
        │  (50 Hz)         │            │                  │
        └────────┬─────────┘            │  Input: sensors  │
                 │                      │  Output: actions │
                 │ radians              └──────────────────┘
                 ▼
        ┌──────────────────────────────────────────────┐
        │   WaveshareHWI (NEW)                         │
        │  ┌────────────────────────────────────────┐ │
        │  │ Conversion Layer:                      │ │
        │  │ • rad_to_servo_pos(radian → 0-2048)   │ │
        │  │ • servo_pos_to_rad(0-2048 → radian)   │ │
        │  │                                        │ │
        │  │ Methods matching HWI interface:        │ │
        │  │ • set_position_all()                   │ │
        │  │ • get_present_positions()              │ │
        │  │ • get_present_velocities()             │ │
        │  │ • turn_on() / turn_off()               │ │
        │  └────────────────────────────────────────┘ │
        └────────────────┬─────────────────────────────┘
                         │
                    servo units
                    (0-2048)
                         │
                ┌────────┴──────────────┐
                │                       │
                ▼                       ▼
        ┌─────────────────┐    ┌──────────────┐
        │ PortHandler &   │    │ Waveshare    │
        │ sms_sts         │    │ scservo_sdk  │
        │ (SDK)           │    │              │
        └────────┬────────┘    └──────────────┘
                 │
      Serial Bus (TTL/RS485)
                 │
    ┌────────────┴────────────────────────────────┐
    │                                             │
    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼
┌─────────────────────────────────────────────────┐
│  14 Waveshare Servos (SC-15 or similar)        │
│  IDs: [10,11,12,13,14, 20,21,22,23,24, 30,31,32,33]
│                                                 │
│  Right Leg: 10-14  (hip/knee/ankle)           │
│  Left Leg:  20-24  (hip/knee/ankle)           │
│  Head:      30-33  (pitch/yaw/roll)           │
│  Neck:      30     (pitch)                    │
└─────────────────────────────────────────────────┘
```

---

## Key Concepts

### RLWalk ← → HWI Interface

The **HWI (Hardware Interface)** is the abstraction layer that:

| Aspect | RLWalk Side | HWI Side | Waveshare Side |
|--------|------------|---------|----------------|
| **Data** | Radians (-π to π) | Converts | 0-2048 units |
| **Method** | `set_position_all()` | Formats | `WritePosEx()` loop |
| **Reading** | `get_present_positions()` | Aggregate | `ReadPos()` loop |
| **Rate** | 50 Hz | Syncs | Serial comm |

### Position Mapping (CRITICAL)

You must calibrate how your servos map to radians:

```python
# Example: assuming ±π maps to full range centered at 1024
servo_pos = (rad / π) * 1024 + 1024

# If your servo is mounted reversed:
servo_pos = 1024 - (rad / π) * 1024

# If your servo uses different range:
servo_pos = ... (depends on your mechanical setup)
```

### Observation Vector (125 dimensions)

The RL policy expects observations in this exact order:
```
[gyro(3), accel(3), gamepad(7), pos(14), vel(14), 
 action(-1)(14), action(-2)(14), action(-3)(14), 
 targets(14), contacts(4), phase(2)]
```

**All of this is handled by `RLWalk.get_obs()`** - you don't need to change it.

---

## Files Modified vs Created

### Created (New Files)
- `waveshare_position_hwi.py` - Hardware interface adapter
- `WAVESHARE_ADAPTATION_GUIDE.md` - Technical documentation
- `SETUP_TESTING_GUIDE.md` - Setup procedures
- `COMPARISON_MIGRATION_REFERENCE.md` - Reference guide
- `test_waveshare_setup.py` - Diagnostic tests
- `README_WAVESHARE_INTEGRATION.md` - This file

### Modified
- `scripts/v2_rl_walk_mujoco.py` - Update import (1 line change)

### Unchanged
- All other RLWalk code (just works with new HWI)
- RL policy loading (ONNX inference)
- Observation assembly
- Control loop timing
- Gamepad input handling
- IMU sensor handling
- Eyes, antennas, sounds, etc.

---

## Calibration (Most Important Part!)

The `rad_to_servo_pos()` function is critical. It must be correct for your specific servo mounts.

### Quick Calibration Process

1. **Manually move each servo to known angles**
   ```python
   # Move servo 10 to different positions and measure
   packet_handler.WritePosEx(10, 0, 500, 30)      # Min
   packet_handler.WritePosEx(10, 1024, 500, 30)   # Center
   packet_handler.WritePosEx(10, 2047, 500, 30)   # Max
   ```

2. **Record what angle each corresponds to physically**
   - Use a protractor or reference angle
   - Measure mechanically where the servo points

3. **Create mapping formula**
   - If linear: `servo_pos = (rad / π) * 1024 + 1024`
   - If reversed: `servo_pos = 1024 - (rad / π) * 1024`
   - If different range: adjust multiplier

4. **Validate with test script**
   ```bash
   python test_waveshare_setup.py --port COM5 --test single
   ```

---

## Testing Sequence

1. **Connection Test**
   ```bash
   python test_waveshare_setup.py --port COM5 --test discovery
   ```
   Should find 14 servos with IDs [10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33]

2. **Position Test**
   ```bash
   python test_waveshare_setup.py --port COM5 --test positions
   ```
   Should read all servo positions

3. **Movement Test**
   ```bash
   python test_waveshare_setup.py --port COM5 --test all_move
   ```
   Servos should move smoothly: center → low → high → center

4. **HWI Test**
   ```bash
   python test_waveshare_setup.py --port COM5 --test hwi
   ```
   Tests WaveshareHWI class integration

5. **Policy Test**
   ```bash
   python scripts/v2_rl_walk_mujoco.py \
       --onnx_model_path="policy.onnx" \
       --duck_config_path="duck_config.json"
   ```
   Monitor for smooth servo motion and control loop timing

---

## Troubleshooting Flowchart

```
Robot doesn't move?
├─ Check serial connection
│  └─ Run: test_waveshare_setup.py --test discovery
├─ Check servo IDs
│  └─ Verify 14 servos found with correct IDs
├─ Check position mapping
│  └─ Verify rad_to_servo_pos() formula is correct
└─ Check observation vector
   └─ Print obs shape in get_obs() - must be (125,)

Robot moves backward?
├─ Servo mounted in reverse
│  └─ Negate formula: servo_pos = 1024 - (rad/π)*1024
├─ Wrong offset values
│  └─ Check duck_config.json joints_offset
└─ Wrong init_pos values
   └─ Check init_pos in waveshare_position_hwi.py

Robot jerky/unstable?
├─ Action scale too large
│  └─ Reduce: action_scale=0.1 (instead of 0.25)
├─ Servo speed too fast
│  └─ Reduce speed parameter in WritePosEx
├─ Observation stale
│  └─ Check sensor update rates
└─ Policy issue
   └─ Check ONNX model compatibility
```

---

## Performance Tuning

### Speed Parameter
In `waveshare_position_hwi.py`, `set_position_all()` method:
```python
speed = 500  # Try: 300-1000 (higher = faster)
```

### Action Scale
In policy call:
```python
RLWalk(..., action_scale=0.25, ...)  # Try: 0.1-0.5
```

### Control Frequency
```bash
python scripts/v2_rl_walk_mujoco.py --control_freq=50  # Default, try 30-100
```

### PID Gains
```python
kps = [30] * 14  # Default, tune per joint
kds = [0] * 14   # Usually no D term
```

---

## Expected Results

Once everything is working:

1. **Servo Discovery**
   - All 14 servos respond to ping
   - IDs match your configuration

2. **Smooth Movement**
   - Servos move back and forth smoothly
   - No twitching or jerky motion
   - All servos respond within 50ms

3. **RL Policy Execution**
   - Robot stands at init_pos
   - Moves legs as if walking
   - Responds to gamepad commands
   - Maintains ~50 Hz control loop

4. **Performance**
   - CPU usage: 20-40% (single core)
   - Policy inference time: <10ms
   - Serial communication: ~5ms
   - Frame rate: 50 Hz (20ms cycles)

---

## Next Steps

1. **Immediate**: Review the architecture guide
   - `WAVESHARE_ADAPTATION_GUIDE.md`

2. **Setup**: Follow the testing guide
   - `SETUP_TESTING_GUIDE.md`

3. **Calibrate**: Determine your servo position mapping
   - Use `test_waveshare_setup.py` for validation

4. **Integrate**: Update imports and run the policy
   - Change 1 line in `v2_rl_walk_mujoco.py`

5. **Validate**: Run diagnostic tests
   - `python test_waveshare_setup.py --test all`

6. **Deploy**: Connect gamepad and let it walk!
   - `python scripts/v2_rl_walk_mujoco.py ...`

---

## Support & References

### Documentation Files
- `WAVESHARE_ADAPTATION_GUIDE.md` - Technical deep-dive
- `SETUP_TESTING_GUIDE.md` - Practical setup steps
- `COMPARISON_MIGRATION_REFERENCE.md` - Protocol comparison

### Test Script
- `test_waveshare_setup.py` - Automated diagnostics
- Usage: `python test_waveshare_setup.py --help`

### Hardware
- Waveshare SC-15 Datasheet (for register addresses)
- Open Duck Mini Documentation
- Your `duck_config.json` (offsets and calibration)

### Contact
If you encounter issues:
1. Run the diagnostic tests first
2. Check the troubleshooting guides
3. Verify calibration with manual servo tests
4. Check ONNX policy compatibility

---

**Good luck with your Waveshare servo integration! 🚀**

The framework is complete - you mainly need to calibrate the position mapping for your specific servo mounts, then it should "just work" with the rest of the Open Duck Mini codebase.

