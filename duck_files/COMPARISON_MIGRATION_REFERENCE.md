"""
Comparison & Migration Reference
================================

This file provides side-by-side comparison of how Open Duck Mini
operates with Feetech vs. Waveshare servos.
"""

# ==============================================================================
# ARCHITECTURE COMPARISON
# ==============================================================================

FEETECH_ARCHITECTURE = """
┌─────────────────────────────────────────────────────────────────┐
│                    RLWalk (v2_rl_walk_mujoco.py)                │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│           rustypot_position_hwi.HWI                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ self.io = rustypot.feetech(port, baudrate)              │  │
│  │ - Handles low-level protocol                            │  │
│  │ - Works directly in radians                             │  │
│  │ - Built-in batch read/write                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│            Feetech Serial Bus Servos (STS3215)                  │
│  - Proprietary protocol                                         │
│  - Radians natively (or wrapped by rustypot)                   │
│  - Can batch multiple commands                                  │
└─────────────────────────────────────────────────────────────────┘


RLWalk doesn't care about servo details - just calls HWI methods:
- hwi.set_position_all(joint_dict)  ← Position in radians
- hwi.get_present_positions()        ← Returns radian array
- hwi.get_present_velocities()       ← Returns rad/s array
- hwi.turn_on() / turn_off()         ← Power management
- hwi.set_kps() / set_kds()          ← PID gains
"""

WAVESHARE_ARCHITECTURE = """
┌─────────────────────────────────────────────────────────────────┐
│                    RLWalk (v2_rl_walk_mujoco.py)                │
│                        (UNCHANGED)                              │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│           waveshare_position_hwi.WaveshareHWI                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ self.port_handler = PortHandler(port)                   │  │
│  │ self.packet_handler = sms_sts(port_handler)             │  │
│  │                                                          │  │
│  │ rad_to_servo_pos(): radians → 0-2048                    │  │
│  │ servo_pos_to_rad(): 0-2048 → radians                    │  │
│  │                                                          │  │
│  │ Provides SAME interface as rustypot_position_hwi:       │  │
│  │ - set_position_all(radians)                             │  │
│  │ - get_present_positions() → radians                     │  │
│  │ - etc.                                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│      Waveshare scservo_sdk (PortHandler + sms_sts)              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ WritePosEx(servo_id, position, speed, acc)              │  │
│  │ ReadPos(servo_id) → position (0-2048)                   │  │
│  │ ReadSpeed(servo_id) → speed (raw units)                 │  │
│  │ set_kps() / set_kds() for PID gains (if available)      │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│      Waveshare Serial Bus Servos (SC-15, SC-12, etc.)           │
│  - St Protocol                                                  │
│  - Position 0-2048 (0-360°)                                     │
│  - Speed in proprietary units                                   │
└─────────────────────────────────────────────────────────────────┘


Key difference: WaveshareHWI provides a "translation layer"
that converts between radians (expected by RLWalk) and Waveshare
servo units (0-2048).
"""

# ==============================================================================
# DATA FLOW COMPARISON
# ==============================================================================

FEETECH_DATA_FLOW = """
Observation Collection:
┌─────────────────────────────────────┐
│ Position from servo (radian)        │  ← self.io.read_present_position()
├─────────────────────────────────────┤
│ Already in radians, add to obs      │  ← dof_pos (shape: 14)
├─────────────────────────────────────┤
│ Concatenate with other obs          │  ← get_obs() returns shape (125,)
└─────────────────────────────────────┘

Policy Inference:
┌─────────────────────────────────────┐
│ obs: [125] from sensors             │  ← ONNX expects this
├─────────────────────────────────────┤
│ action = policy.infer(obs)          │  ← Output: [14] normalized
├─────────────────────────────────────┤
│ target_pos = init_pos + action*0.25 │  ← Still radians
└─────────────────────────────────────┘

Command Sending:
┌─────────────────────────────────────┐
│ target_pos: [14] radians            │
├─────────────────────────────────────┤
│ self.io.write_goal_position()       │  ← rustypot handles conversion
├─────────────────────────────────────┤
│ Feetech servo receives command      │  ← Internal conversion to units
└─────────────────────────────────────┘
"""

WAVESHARE_DATA_FLOW = """
Observation Collection:
┌─────────────────────────────────────┐
│ Position from servo (0-2048)        │  ← ReadPos(servo_id)
├─────────────────────────────────────┤
│ Convert to radians                  │  ← servo_pos_to_rad()
├─────────────────────────────────────┤
│ Add to observation (as radians)     │  ← dof_pos (shape: 14)
├─────────────────────────────────────┤
│ Concatenate with other obs          │  ← get_obs() returns shape (125,)
└─────────────────────────────────────┘

Policy Inference:
┌─────────────────────────────────────┐
│ obs: [125] from sensors             │  ← ONNX expects this
├─────────────────────────────────────┤
│ action = policy.infer(obs)          │  ← Output: [14] normalized
├─────────────────────────────────────┤
│ target_pos = init_pos + action*0.25 │  ← Still radians
└─────────────────────────────────────┘

Command Sending:
┌─────────────────────────────────────┐
│ target_pos: [14] radians            │
├─────────────────────────────────────┤
│ Convert to servo units (0-2048)     │  ← rad_to_servo_pos()
├─────────────────────────────────────┤
│ WritePosEx(servo_id, position, ...) │  ← Send to Waveshare
├─────────────────────────────────────┤
│ Waveshare servo receives command    │
└─────────────────────────────────────┘
"""

# ==============================================================================
# METHOD MAPPING
# ==============================================================================

METHOD_MAPPING = """
RLWalk calls these HWI methods:
─────────────────────────────────────────────────────────────────

METHOD                          FEETECH IMPL              WAVESHARE IMPL
─────────────────────────────────────────────────────────────────
hwi.turn_on()                   Set low KP              Set low KP
                                Move to init_pos        Move to init_pos
                                Set high KP             Set high KP

hwi.turn_off()                  Call rustypot API       WriteEx with torque=0

hwi.set_position_all(dict)      Call rustypot API       Loop + WritePosEx
                                (batch)                 (individual)

hwi.get_present_positions()     Call rustypot API       Loop ReadPos
                                Returns radians         Convert to radians

hwi.get_present_velocities()    Call rustypot API       Loop ReadSpeed
                                Returns rad/s           Convert to rad/s

hwi.set_kps(list)              Call rustypot API        Store in self.kps
                                                        (register varies)

hwi.set_kds(list)              Call rustypot API        Store in self.kds
                                                        (register varies)
─────────────────────────────────────────────────────────────────

Both implementations return the SAME data types and ranges,
so RLWalk doesn't need to change at all.
"""

# ==============================================================================
# UNIT CONVERSION DETAILS
# ==============================================================================

UNIT_CONVERSION = """
CRITICAL: Understanding the conversions
════════════════════════════════════════════════════════════════

RADIANS (Open Duck Mini internal)
─────────────────────────────────
- Used throughout RLWalk code
- Policy trained on radian observations
- Range: typically -π to π (but varies per joint)
- Example: left_hip_pitch init_pos = -0.63 rad ≈ -36°

SERVO UNITS (Waveshare native)
──────────────────────────────
- Position range: 0 to 2048
- Maps to: 0° to 360° (or 0° to 270°, depends on servo model)
- 1 unit = 0.176° (for 360° model)
- Center position: 1024 (180°)

CONVERSION FORMULA (assumption: ±π maps to full range)
─────────────────────────────────────────────────────
servo_pos = (rad / π) * (2048/2) + 1024
          = (rad / π) * 1024 + 1024

Example:
  0 rad     → (0/π) * 1024 + 1024 = 1024 (center)
  π/2 rad   → (0.5) * 1024 + 1024 = 1536 (270°)
  -π/2 rad  → (-0.5) * 1024 + 1024 = 512 (90°)
  π rad     → (1) * 1024 + 1024 = 2048 (360°/0°)
  -π rad    → (-1) * 1024 + 1024 = 0 (360° wrapped)

INVERSE (servo units → radians)
────────────────────────────────
rad = ((servo_pos - 1024) / 1024.0) * π

SPECIAL CASES
─────────────
Some servos may be:
- Mounted in reverse (negate the conversion)
- Have different center positions (not 1024)
- Use different mechanical ranges (not ±π)

Must CALIBRATE per joint based on mechanical setup.
"""

# ==============================================================================
# PROTOCOL DIFFERENCES
# ==============================================================================

PROTOCOL_COMPARISON = """
Feetech vs Waveshare: Protocol Level Differences
════════════════════════════════════════════════

FEETECH (via rustypot):
──────────────────────
- Purpose: Servo motion control via serial bus
- Library: rustypot (Python wrapper)
- Interface: High-level
  
  Example:
    self.io.write_goal_position([id1, id2], [pos1, pos2])
    -> Handles packet construction, CRC, timing internally
    -> Returns immediately
    
  Batch operations:
    io.write_goal_position([10, 11, 12, ...], [pos1, pos2, pos3, ...])
    -> All servos move simultaneously
    
  Feedback:
    positions = io.read_present_position([10, 11, 12, ...])
    -> Returns list of positions
    

WAVESHARE (via scservo_sdk):
───────────────────────────
- Purpose: Low-level protocol communication
- Library: scservo_sdk (Python binding to C protocol)
- Interface: Lower-level

  Example:
    packet_handler.WritePosEx(servo_id, pos, speed, acc)
    -> Constructs packet, sends to single servo
    -> Returns communication result
    
  Individual commands:
    for servo_id in [10, 11, 12, ...]:
        packet_handler.WritePosEx(servo_id, pos, speed, acc)
    -> Must loop through servos
    
  Feedback:
    pos, comm_result, error = packet_handler.ReadPos(servo_id)
    -> Returns single servo data + communication status


KEY DIFFERENCE:
───────────────
Waveshare SDK requires handling individual servo commands,
while rustypot can batch them.

WaveshareHWI compensates by looping internally in set_position_all().
"""

# ==============================================================================
# MIGRATION CHECKLIST
# ==============================================================================

MIGRATION_CHECKLIST = """
Step-by-step migration from Feetech to Waveshare
═════════════════════════════════════════════════

PREPARATION:
☐ 1. Install Waveshare SDK in your environment
☐ 2. Identify serial port (COM5, /dev/ttyACM0, etc.)
☐ 3. Discover servo IDs (scan_servos())
☐ 4. Verify servo power and connections

IMPLEMENTATION:
☐ 5. Add waveshare_position_hwi.py to mini_bdx_runtime/
☐ 6. Update imports in v2_rl_walk_mujoco.py
☐ 7. Adjust SDK path in waveshare_position_hwi.py if needed

CALIBRATION:
☐ 8. Calibrate rad_to_servo_pos() for each servo mount
☐ 9. Test center positions (servo should face forward)
☐ 10. Test full range movements (ensure no binding)

INTEGRATION:
☐ 11. Run discovery test (servo_scan())
☐ 12. Run movement tests (test_smooth_movement.py)
☐ 13. Run full RL policy with policy.run()

VALIDATION:
☐ 14. Observe smooth servo motion
☐ 15. Check observation vector (should be 125 elements)
☐ 16. Verify control loop frequency (50 Hz)
☐ 17. Tune action_scale if needed (start at 0.25)

TROUBLESHOOTING:
☐ 18. Check serial communication (no timeouts)
☐ 19. Verify sensor readings are valid (not NaN)
☐ 20. Monitor CPU usage (should be low)
"""

# ==============================================================================
# QUICK REFERENCE TABLE
# ==============================================================================

QUICK_REFERENCE = """
│ ASPECT                 │ FEETECH           │ WAVESHARE         │
├────────────────────────┼───────────────────┼───────────────────┤
│ Position Units         │ Radians           │ 0-2048 (raw)      │
│ Library                │ rustypot          │ scservo_sdk       │
│ Batch Commands         │ Yes (built-in)    │ Manual loop       │
│ Feedback Range         │ Continuous        │ 0-2048 discrete   │
│ Conversion Needed      │ No (abstracted)   │ YES (crucial)     │
│ Speed Parameter        │ Built-in          │ WritePosEx param  │
│ KP/KD Support          │ Yes               │ Limited (varies)  │
│ Calibration Effort     │ Low               │ HIGH              │
│ Protocol Complexity    │ High (abstracted) │ Medium (visible)  │
├────────────────────────┼───────────────────┼───────────────────┤
│ FOR RLWalk POLICY      │ Just works        │ Need HWI adapter  │
│ Porting Effort         │ N/A               │ ~2-4 hours        │
│ Get Working            │ N/A               │ ~1-2 hours        │
│ Optimize & Tune        │ N/A               │ ~1-2 hours        │
└────────────────────────┴───────────────────┴───────────────────┘
"""

# ==============================================================================
# COMMON ISSUES & SOLUTIONS
# ==============================================================================

TROUBLESHOOTING = """
PROBLEM: "RL Policy moves servos but in wrong direction"
CAUSE: rad_to_servo_pos() conversion is backwards for that servo
SOLUTION: Negate the formula or swap position limits
  Original: servo_pos = (rad / π) * 1024 + 1024
  Fixed:    servo_pos = 1024 - (rad / π) * 1024

PROBLEM: "Servos move very slowly / take forever to reach target"
CAUSE: speed parameter in WritePosEx too low
SOLUTION: Increase speed (default 500 → try 1000-2000)

PROBLEM: "Observation vector has wrong shape (not 125)"
CAUSE: get_present_positions() returning None or wrong count
SOLUTION: 
  1. Check servo IDs match self.joints
  2. Verify ReadPos returns valid data
  3. Check ignore list doesn't exclude wrong joints

PROBLEM: "Policy outputs zeros / robot paralyzed"
CAUSE: Observation contains invalid data (NaN, zeros)
SOLUTION:
  1. Print obs in get_obs(): print(f"Obs: {obs}")
  2. Check IMU data validity
  3. Check all servo reads succeed
  4. Verify observation length is exactly 125

PROBLEM: "Servo jerks / unstable movement"
CAUSE: Update rate too fast or position jumps too large
SOLUTION:
  1. Reduce action_scale (e.g., 0.25 → 0.1)
  2. Reduce speed or increase acceleration parameter
  3. Check position mapping calibration
  4. Reduce control_freq from 50 to 30 Hz

PROBLEM: "COMM_TIMEOUT / no servo response"
CAUSE: Serial communication failure
SOLUTION:
  1. Check USB cable connection
  2. Verify baud rate (1000000 for SC-15, check datasheet)
  3. Test with servo_scan() - should find all 14 servos
  4. Check for multiple programs accessing port
"""

# ==============================================================================
# REFERENCES & DATASHEETS
# ==============================================================================

REFERENCES = """
Key Resources for Migration
════════════════════════════

1. Waveshare SC-15 Servo Datasheet
   - Register map (Position, Speed, PID gains, etc.)
   - Protocol specification (WritePosEx, ReadPos, etc.)
   - Electrical specifications (voltage, current, torque)
   - Motion profiles and timing

2. Open Duck Mini Documentation
   - Hardware setup guide
   - Joint calibration procedures
   - Policy training & inference details

3. RL Training Details (you may have)
   - Policy.onnx model file
   - Duck_config.json (offset values)
   - polynomial_coefficients.pkl (gait reference)

4. Waveshare Forum / Support
   - Common issues and solutions
   - Register address clarifications
   - Hardware troubleshooting

Key Parameters to Find in Datasheet:
─────────────────────────────────────
□ Position range (0-2048? 0-4095? 0-2047?)
□ Speed units and range
□ Acceleration units and range
□ KP/KD register addresses
□ Torque enable register address
□ Default baud rate and changeable rates
□ Max current and voltage
□ Operating temperature range
"""

print(FEETECH_ARCHITECTURE)
print("\n" + "="*71 + "\n")
print(WAVESHARE_ARCHITECTURE)
print("\n" + "="*71 + "\n")
print(METHOD_MAPPING)
print("\n" + "="*71 + "\n")
print(UNIT_CONVERSION)
print("\n" + "="*71 + "\n")
print(QUICK_REFERENCE)
