# Visual Guide: Open Duck Mini RL Policy with Waveshare Servos

## Overview Diagram

```
YOUR OPEN DUCK MINI ROBOT RUNNING RL POLICY
════════════════════════════════════════════════════════════════

                    UNCHANGED COMPONENTS
                    ════════════════════
                           
                    ┌──────────────────────┐
                    │   ONNX Policy File   │
                    │  (trained neural net)│
                    └──────────────────────┘
                              △
                              │ observation vector (125 values)
                              │
                    ┌──────────────────────────────┐
                    │     RLWalk Main Loop         │
                    │  • Collect sensor data       │
                    │  • Run policy inference      │
                    │  • Send servo commands       │
                    │  • Control at 50 Hz          │
                    └──────────┬───────────────────┘
                              │ radians (joint targets)
                              │
                              ▼
                    ╔══════════════════════════════╗
                    ║   WaveshareHWI (NEW!)        ║
                    ║  • Converts rad ↔ servo pos  ║
                    ║  • Provides HWI interface    ║
                    ║  • Manages serial comm       ║
                    ╚══════════════╦═══════════════╝
                                   │ servo position (0-2048)
                                   │
                         ┌─────────┴──────────┐
                         │                    │
                    ┌────▼─────┐        ┌────▼─────┐
                    │SerialPort│        │ scservo  │
                    │ Handler   │        │ sdk      │
                    └────┬─────┘        └────┬─────┘
                         │                    │
                         └────────┬───────────┘
                                  │
                        RS485 Serial Bus
                                  │
        ┌────────────────────────┬┴────────────────────────┐
        │                        │                         │
   ┌────▼─────┐           ┌────▼─────┐           ┌────▼─────┐
   │ Servo 10 │           │ Servo 11 │           │ Servo 14 │
   │ (R Hip Y)│           │ (R Hip R)│ ......... │ (R Ankle)│
   └──────────┘           └──────────┘           └──────────┘
        │                      │                         │
   ┌────▼─────┐           ┌────▼─────┐           ┌────▼─────┐
   │ Servo 20 │           │ Servo 21 │           │ Servo 24 │
   │ (L Hip Y)│           │ (L Hip R)│ ......... │ (L Ankle)│
   └──────────┘           └──────────┘           └──────────┘
        │                      │                         │
   ┌────▼─────┐           ┌────▼─────┐           ┌────▼─────┐
   │ Servo 30 │           │ Servo 31 │           │ Servo 33 │
   │ (Head PY)│           │(Head Pitch)            │(HeadRoll)│
   └──────────┘           └──────────┘           └──────────┘


OBSERVATION DATA FLOW (How Sensors Feed the Policy)
════════════════════════════════════════════════════

State from Robot:
┌──────────────────────────────────────────────────────┐
│  Sensors (Real-Time)                                 │
├──────────────────────────────────────────────────────┤
│  • IMU (gyroscope) → 3D angular velocity             │
│  • IMU (accelerometer) → 3D acceleration             │
│  • 14 Joint positions → from servo.ReadPos()         │
│  • 14 Joint velocities → from servo.ReadSpeed()     │
│  • 4 Contact sensors → feet touching ground?         │
│  • Gamepad input → user commands                     │
│  • Previous actions → last 3 control steps           │
│  • Gait phase → sin/cos of walking cycle            │
└──────────────────────────────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │  Assemble Observation   │
                │  (RLWalk.get_obs())     │
                │                         │
                │  Concatenate in order:  │
                │  gyro(3)                │
                │  accel(3)               │
                │  gamepad(7)             │
                │  positions(14)          │
                │  velocities(14)         │
                │  action_prev(14)        │
                │  action_prev2(14)       │
                │  action_prev3(14)       │
                │  motor_targets(14)      │
                │  contacts(4)            │
                │  phase(2)               │
                │  ─────────────────────  │
                │  TOTAL: 125 elements    │
                └────────────┬────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │   Policy Inference      │
                │  policy.infer(obs)      │
                │                         │
                │  Neural Network:        │
                │  125 inputs             │
                │  → 14 outputs           │
                │  Range: [-1, 1]         │
                └────────────┬────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │  Action Processing      │
                │                         │
                │  motor_targets =        │
                │  init_pos +             │
                │  action * scale         │
                │                         │
                │  (0.25 = safe speed)    │
                └────────────┬────────────┘
                              │
                              ▼
                    Send to HWI Layer


STATE MACHINE: Robot Startup Sequence
══════════════════════════════════════════════════════════════

       powershell RLWalk
              │
              ▼
    ┌──────────────────────┐
    │  Instantiate RLWalk  │
    │  - Load duck_config  │
    │  - Load ONNX model   │
    │  - Create WaveshareHWI
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │   hwi.turn_on()      │
    │  1. Set low torque   │────────┐
    │     (KP = 2)         │        │ 0.5s
    │                      │        │
    │  2. Move to init_pos ├────────┤ 2.5s
    │     (safe position)  │        │
    │                      │        │
    │  3. Set high torque  ├────────┤ 0.5s
    │     (KP = 30)        │        │
    └──────┬───────────────┘        │
           │                        Total: ~3.5s
           ├────────────────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Initialize IMU      │
    │  Initialize Gamepad  │
    │  Initialize Sensors  │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │  Enter Main Loop     │◄─────────────────────┐
    │  (50 Hz, 20ms/iter)  │                      │
    │                      │                      │
    │  ┌────────────────┐  │  ┌──────────────┐   │
    │  │ Collect Obs    │  │  │Timer: 20ms   │   │
    │  │ Run Policy     │  │  └──────────────┘   │
    │  │ Send Commands  │  │                      │
    │  └────────────────┘  │                      │
    │                      │                      │
    │ Press Ctrl+C to exit └──────────────────────┘
    │      │
    │      ▼
    │ ┌──────────────────┐
    │ │ hwi.turn_off()   │
    │ | Disable torque   │
    │ └──────────────────┘
    │      │
    └──────▼───────→ exitprogram


CONTROL TIMING: 50 Hz Main Loop Details
════════════════════════════════════════════════════════════════

Time (ms) │ Component                      │ Duration
──────────┼────────────────────────────────┼──────────
0         │┌─ Start iteration              │
          ││                                │
1-3       │├─ Collect IMU data             │ ~2ms
          ││  (read accel + gyro)           │
          ││                                │
4-8       │├─ Read servo positions         │ ~4ms
          ││  (14 servos × ReadPos)         │
          ││                                │
9-12      │├─ Read servo velocities        │ ~3ms
          ││  (14 servos × ReadSpeed)       │
          ││                                │
13-14     │├─ Assemble observation         │ ~1ms
          ││  (concatenate 125 values)      │
          ││                                │
15-18     │├─ Policy inference             │ ~3-5ms
          ││  (ONNX model forward pass)     │
          ││                                │
19-20     │├─ Action post-processing       │ ~1ms
          ││  (scaling, filtering)          │
          ││                                │
21-25     │├─ Send servo commands          │ ~4-5ms
          ││  (14 × WritePosEx)             │
          ││                                │
26-27     │├─ Sleep to maintain timing     │ varies
          ││  (if loop faster than 50Hz)    │
          ││                                │
28        │└─ Loop iteration complete      │
──────────┼────────────────────────────────┼──────────
      Total: ~20ms target (50 Hz)          │


JOINT CONFIGURATION: 14 DOF Layout
════════════════════════════════════════════════════════════════

Right Leg (IDs 10-14):
────────────────────
    10: right_hip_yaw (rotate around vertical axis)
    11: right_hip_roll (side-to-side tilt)
    12: right_hip_pitch (forward/backward thrust)
    13: right_knee (fold leg)
    14: right_ankle (flex foot)

Left Leg (IDs 20-24):
──────────────────
    20: left_hip_yaw
    21: left_hip_roll
    22: left_hip_pitch
    23: left_knee
    24: left_ankle

Head & Neck (IDs 30-33):
──────────────────────
    30: neck_pitch (up/down)
    31: head_pitch (up/down)
    32: head_yaw (left/right)
    33: head_roll (tilt)

         [30]─[31]
         [32]─[33]    ← Head
              │
         [20]─[21]    ← Left Hip
              [22]    ← Left Pitch
              [23]    ← Left Knee
              [24]    ← Left Ankle
           /       \\
          /  LEFT    \\
         LEG           RIGHT LEG
                       
         [10]─[11]    ← Right Hip
              [12]    ← Right Pitch
              [13]    ← Right Knee
              [14]    ← Right Ankle


UNIT CONVERSIONS: Radians ↔ Servo Position
════════════════════════════════════════════════════════════════

RLWalk operates in RADIANS (human-friendly):
─────────────────────────────────────────
    0 rad     = center position
    π/2 rad   = 90° rotation
    -π/2 rad  = -90° rotation
    π rad     = 180° rotation

Waveshare servos operate in RAW UNITS (0-2048):
───────────────────────────────────────────────
    0-2048    = full rotation range
    1024      = center position
    512       = quarter rotation
    2047      = near end position

Conversion Formula (MUST CALIBRATE!):
─────────────────────────────────────
    servo_position = (radian / π) × 1024 + 1024

Examples:
    0 rad       → (0 / π) × 1024 + 1024 = 1024 (center)
    π/2 rad     → (0.5) × 1024 + 1024 = 1536
    -π/2 rad    → (-0.5) × 1024 + 1024 = 512
    π rad       → (1.0) × 1024 + 1024 = 2048
    -π rad      → (-1.0) × 1024 + 1024 = 0

⚠️ CRITICAL: This formula assumes your servo is mounted
   with positive radian = clockwise rotation. Verify with
   physical testing and adjust if reversed!


DATA TYPES & SHAPES: Understanding the Numpy Arrays
═════════════════════════════════════════════════════

Observation Vector (obs):
────────────────────────
    Type: numpy.ndarray
    Shape: (125,)
    Range: varies per element
    
    obs[0:3]    = gyro [rad/s]
    obs[3:6]    = accel [m/s²]
    obs[6:13]   = gamepad commands [0-1]
    obs[13:27]  = positions [rad]
    obs[27:41]  = velocities [rad/s]
    obs[41:55]  = action from t-1 [normalized]
    obs[55:69]  = action from t-2 [normalized]
    obs[69:83]  = action from t-3 [normalized]
    obs[83:97]  = motor targets [rad]
    obs[97:101] = contact sensors [0-1]
    obs[101:103]= gait phase [sin, cos]

Policy Action Output (action):
──────────────────────────────
    Type: numpy.ndarray
    Shape: (14,)
    Range: [-1.0, 1.0] (normalized)
    
    action[0:5]   = left leg (hip/knee/ankle)
    action[5:9]   = head (pitch/yaw/roll/neck)
    action[9:14]  = right leg (hip/knee/ankle)

Motor Targets (motor_targets):
──────────────────────────────
    Type: numpy.ndarray
    Shape: (14,)
    Range: determined by init_pos + action*scale
    Units: radians
    
    Mapping to servos via joint dictionary in HWI


DEBUGGING: Common Print Statements
═══════════════════════════════════

To debug your integration, add these prints:

In RLWalk.get_obs():
─────────────────────
    print(f"Obs shape: {obs.shape}, dtype: {obs.dtype}")
    if np.any(np.isnan(obs)):
        print("WARNING: NaN values in observation!")

In RLWalk.run():
─────────────────
    print(f"Action shape: {action.shape}")
    print(f"Min action: {action.min()}, Max action: {action.max()}")

In WaveshareHWI.set_position_all():
────────────────────────────────
    print(f"Setting position for {joint_name}: {pos:.3f} rad → {servo_pos} units")

In WaveshareHWI.get_present_positions():
─────────────────────────────────────────
    print(f"Read {len(servo_ids)} positions from servos")
    if any(np.isnan(positions)):
        print("ERROR: NaN in position reading!")


SUCCESS INDICATORS
═════════════════════════════════════════════════════════════════

✓ Serial Connection OK:
  └─ test_waveshare_setup.py --test discovery
     Shows all 14 servos with valid position values

✓ Position Mapping OK:
  └─ Robot stands at init_pos when powered on
  └─ No servo appears inverted
  └─ test_waveshare_setup.py --test single works

✓ Policy Integrated OK:
  └─ RLWalk initializes without errors
  └─ Policy inference completes each cycle
  └─ Control loop runs at ~50 Hz

✓ Observation Valid:
  └─ get_obs() returns exactly 125 values
  └─ No NaN or inf values in observation
  └─ Sensor readings change with robot movement

✓ Robot Walking OK:
  └─ Servos move smoothly when policy runs
  └─ Gait is coordinated (legs alternate)
  └─ Responds to gamepad commands
  └─ No jerking or sudden movements

✓ Full System OK:
  └─ 20-40% CPU usage (single core)
  └─ <500ms latency from sensor to servo
  └─ Walks forward without external support
  └─ Can recover from small perturbations

