# Waveshare Servo Integration - Master Checklist

## Pre-Integration Checklist

### Hardware Verification
- [ ] All 14 servos powered (check LED indicators)
- [ ] USB cable connected to computer
- [ ] Serial connection stable (no loose connectors)
- [ ] Servo IDs known (run discovery test first)
- [ ] Baud rate compatible (1000000 typical for SC-15)

### Software Prerequisites
- [ ] Python 3.7+ installed
- [ ] numpy installed (`pip install numpy`)
- [ ] onnxruntime installed (`pip install onnxruntime`)
- [ ] Waveshare SDK in Python path
- [ ] duck_config.json available
- [ ] policy.onnx file available

### File Organization
- [ ] `waveshare_position_hwi.py` exists in workspace
- [ ] Servo SDK files accessible
- [ ] Test script can be run
- [ ] Documentation files downloaded/accessible

---

## Setup Phase Checklist

### Step 1: Environment Setup
- [ ] Python environment created/activated
- [ ] Required packages installed
- [ ] PYTHONPATH includes Waveshare SDK
- [ ] `import scservo_sdk` works without errors

### Step 2: Hardware Discovery
- [ ] Serial port identified (COM5, /dev/ttyACM0, etc.)
- [ ] test_waveshare_setup.py --test discovery runs
- [ ] All 14 servos found (expected IDs: 10-14, 20-24, 30-33)
- [ ] Position values readable from each servo
- [ ] No timeout or communication errors

### Step 3: Individual Servo Testing
- [ ] Each servo responds to WritePosEx command
- [ ] Each servo can be moved to known positions
- [ ] Center position (1024) works correctly
- [ ] Min position (512) works correctly
- [ ] Max position (1536) works correctly

### Step 4: Position Mapping Calibration
- [ ] Mechanical measurements taken for each servo mount
- [ ] Conversion formula created: `rad_to_servo_pos()`
- [ ] Inverse formula created: `servo_pos_to_rad()`
- [ ] Formula tested with manual servo movements
- [ ] Position mapping validated (within tolerance)

### Step 5: WaveshareHWI Integration
- [ ] Copy `waveshare_position_hwi.py` to correct location
- [ ] Update SDK path in waveshare_position_hwi.py if needed
- [ ] Update position mapping formulas in HWI
- [ ] Test HWI class initialization
- [ ] Test HWI methods (get_pos, set_pos, turn_on, etc.)

---

## Integration Phase Checklist

### Step 6: Update v2_rl_walk_mujoco.py
- [ ] Open `scripts/v2_rl_walk_mujoco.py`
- [ ] Find line with `from mini_bdx_runtime.rustypot_position_hwi import HWI`
- [ ] Change to: `from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI as HWI`
- [ ] Save file
- [ ] Verify syntax (no errors in IDE)

### Step 7: Configuration Verification
- [ ] duck_config.json exists and is readable
- [ ] Policy ONNX file exists and is readable
- [ ] Joint offsets in duck_config match your servos
- [ ] Initial positions make physical sense
- [ ] KP/KD values reasonable (default: KP=30, KD=0)

### Step 8: RLWalk Initialization Test
- [ ] Run RLWalk with `--help` flag to see options
- [ ] Create simple test script that creates RLWalk instance
- [ ] Verify HWI initializes without errors
- [ ] Check that robot moves to init_pos
- [ ] Confirm that all 14 joints respond

---

## Validation Phase Checklist

### Step 9: Observation Vector Validation
- [ ] Observation vector has exactly 125 elements
- [ ] No NaN or inf values in observation
- [ ] Sensor readings change when robot moves
- [ ] Gyro and accel values in reasonable range
- [ ] Joint positions change when servos move

### Step 10: Policy Inference Validation
- [ ] ONNX model loads without errors
- [ ] Policy inference completes in <10ms
- [ ] Action output has 14 values
- [ ] Action values in [-1, 1] range
- [ ] Different observations produce different actions

### Step 11: Motor Response Validation
- [ ] Motor targets computed from policy
- [ ] Motor targets scaled by action_scale
- [ ] Servos move in direction policy commands
- [ ] No inverted movements (check calibration if inverted)
- [ ] Movement is smooth and continuous

### Step 12: Control Loop Timing Validation
- [ ] Control loop runs at ~50 Hz (20ms per cycle)
- [ ] No missed cycles (check loop timing)
- [ ] CPU usage reasonable (20-40%)
- [ ] No deadlocks or freeze-ups
- [ ] Graceful exit on Ctrl+C

---

## Functional Testing Checklist

### Step 13: Basic Movement Test
- [ ] Robot stands at init_pos
- [ ] All servos respond to commands
- [ ] Movements are coordinated between leg joints
- [ ] Head follows gamepad input (if enabled)
- [ ] No single servo fails or gets stuck

### Step 14: Smooth Operation Test
- [ ] No jerky or twitchy movements
- [ ] No sudden position jumps
- [ ] No oscillation or overshoot
- [ ] Transitions between postures are smooth
- [ ] Runtime is stable (runs for >1 minute without issues)

### Step 15: Environmental Response Test
- [ ] Gamepad input modulates walking (if enabled)
- [ ] Speed changes with input magnitude
- [ ] Direction changes with input direction
- [ ] Transitions are smooth
- [ ] Robot maintains balance (doesn't fall over)

### Step 16: Recovery & Safety Test
- [ ] Robot can recover from small perturbations
- [ ] No runaway motion or loss of control
- [ ] Ctrl+C stops robot smoothly
- [ ] All servos disable on exit (no holding positions)
- [ ] No error messages after clean shutdown

---

## Performance Tuning Checklist

### Step 17: Speed Optimization
- [ ] Current servo speed parameter noted (default: 500)
- [ ] Increase speed if robot too slow (try 1000)
- [ ] Decrease speed if movements too jerky (try 250)
- [ ] Find balance between smoothness and responsiveness
- [ ] Document final speed parameter

### Step 18: Action Scale Optimization
- [ ] Current action_scale noted (default: 0.25)
- [ ] Increase if robot needs more power (try 0.35)
- [ ] Decrease if robot too aggressive (try 0.15)
- [ ] Find balance between control and power
- [ ] Document final action_scale

### Step 19: PID Gain Optimization
- [ ] Current KP values noted (default: 30 for body, 8 for head)
- [ ] Current KD values noted (default: 0 for all)
- [ ] Increase KP if tracking is loose (try +5)
- [ ] Decrease KP if oscillating (try -5)
- [ ] Validate that joints reach target positions
- [ ] Document final PID gains

### Step 20: Sensor Calibration
- [ ] IMU calibration complete (zero rates and accels)
- [ ] Joint offset values validated
- [ ] Contact sensor thresholds set correctly
- [ ] All sensor readings in expected range
- [ ] Observation vector makes physical sense

---

## Documentation Checklist

### Step 21: Documentation Review
- [ ] Read README_WAVESHARE_INTEGRATION.md
- [ ] Review WAVESHARE_ADAPTATION_GUIDE.md sections 1-3
- [ ] Skim SETUP_TESTING_GUIDE.md for reference
- [ ] Bookmark VISUAL_GUIDE.md for architecture understanding
- [ ] Save COMPARISON_MIGRATION_REFERENCE.md for future reference

### Step 22: Configuration Documentation
- [ ] Document your servo ID mapping
- [ ] Document position mapping formulas
- [ ] Document final parameters (speed, action_scale, PID)
- [ ] Document any hardware-specific modifications
- [ ] Create README for future reference

### Step 23: Test Results Documentation
- [ ] Save test_waveshare_setup.py output
- [ ] Document any servo issues encountered
- [ ] Note any calibration challenges
- [ ] Record final performance metrics
- [ ] Document recovery procedures for future issues

---

## Deployment Checklist

### Step 24: Pre-Deployment Testing
- [ ] All automated tests pass (test_waveshare_setup.py)
- [ ] Manual movement tests successful
- [ ] Policy operates correctly
- [ ] No console errors or warnings
- [ ] Robot stable for >5 minutes without intervention

### Step 25: Deployment Preparation
- [ ] Clear any debug prints from code
- [ ] Set conservative parameters initially (lower speed, action_scale)
- [ ] Create backup of working configuration
- [ ] Document startup procedure
- [ ] Have recovery procedure documented

### Step 26: Live Operation
- [ ] Start in safe environment (no obstacles)
- [ ] Have someone supervise operation
- [ ] Monitor for any anomalies
- [ ] Test gamepad control (if enabled)
- [ ] Verify smooth operation over extended runtime
- [ ] Document any issues for future optimization

### Step 27: Post-Deployment
- [ ] Save any learned configurations
- [ ] Document lessons learned
- [ ] Update documentation with your findings
- [ ] Create backup of final configuration
- [ ] Plan for future optimization/upgrades

---

## Troubleshooting Checklist

### If Servo Discovery Fails
- [ ] Verify correct serial port (check Device Manager)
- [ ] Check USB cable connection
- [ ] Verify servo IDs haven't changed
- [ ] Try resetting servo bus (power cycle)
- [ ] Check baud rate configuration
- [ ] Run: `test_waveshare_setup.py --port COM5 --test discovery`

### If Position Reading Fails
- [ ] Verify all servos respond to ping
- [ ] Check servo power supply
- [ ] Check for loose RS485 connections
- [ ] Verify servo firmware is compatible
- [ ] Run: `test_waveshare_setup.py --port COM5 --test positions`

### If Movement is Jerky
- [ ] Check position mapping calibration
- [ ] Increase speed parameter (default 500 → try 1000)
- [ ] Increase acceleration parameter
- [ ] Check KP gains (may be too high)
- [ ] Reduce action_scale (0.25 → try 0.1)

### If Robot Moves Backward
- [ ] Verify position mapping formula
- [ ] Check servo mechanical mounting
- [ ] Run calibration test: `test_waveshare_setup.py --test single`
- [ ] Negate conversion formula if needed
- [ ] Verify in physical setup

### If Policy Won't Infer
- [ ] Check ONNX model file exists and readable
- [ ] Verify policy input shape (must be 125)
- [ ] Check observation vector assembly
- [ ] Verify no NaN values in observation
- [ ] Run: `python -c "import onnxruntime; print(onnxruntime.__version__)"`

### If Control Loop is Slow
- [ ] Check CPU usage (may be bottleneck)
- [ ] Verify serial communication speed
- [ ] Reduce observation dimensions if possible
- [ ] Profile code to find bottleneck
- [ ] Consider reducing frequency temporarily

### If Robot Falls Over
- [ ] Check init_pos values are reasonable
- [ ] Increase action_scale (movements too timid)
- [ ] Lower control frequency temporarily
- [ ] Check IMU calibration
- [ ] Verify servo synchronization

---

## Final Validation Checklist

### Before Calling It "Done"
- [ ] All automated tests pass
- [ ] Manual movement tests successful
- [ ] Policy operates smoothly
- [ ] Performance within specification
- [ ] Documentation complete
- [ ] Configuration saved
- [ ] Backup created
- [ ] Recovery procedures documented

### Signs of Success
- ✓ All 14 servos discovered and responsive
- ✓ Robot stands at init_pos on startup
- ✓ Smooth coordinated movements
- ✓ Policy inference working
- ✓ Control loop at 50 Hz
- ✓ No error messages
- ✓ Graceful shutdown
- ✓ Extended runtime stable (>10 minutes)

---

## Quick Reference

### Most Used Commands
```bash
# Test discovery
python test_waveshare_setup.py --port COM5 --test discovery

# Test all
python test_waveshare_setup.py --port COM5 --test all

# Run policy
python scripts/v2_rl_walk_mujoco.py --onnx_model_path=policy.onnx --duck_config_path=duck_config.json

# Test single servo
python test_waveshare_setup.py --port COM5 --test single --servo-id 10 --position 1024
```

### Key Files
- Adapter: `mini_bdx_runtime/mini_bdx_runtime/waveshare_position_hwi.py`
- Script to update: `scripts/v2_rl_walk_mujoco.py` (line 6)
- Tests: `test_waveshare_setup.py`
- Config: `duck_config.json`
- Model: `policy.onnx`

### Key Parameters to Tune
- `speed` in WritePosEx (default: 500)
- `action_scale` in RLWalk (default: 0.25)
- `control_freq` (default: 50)
- `KP` gains (default: 30 body, 8 head)
- `position_mapping` formula (calibration-dependent)

---

## Estimated Timeline

| Phase | Duration | Critical Items |
|-------|----------|-----------------|
| Setup & Discovery | 30 min | Servo communication |
| Calibration | 1-2 hours | Position mapping |
| Integration | 30 min | Import changes |
| Validation | 1 hour | Observation, policy, movement |
| Tuning | 1-2 hours | Speed, scale, PID gains |
| Deployment | 30 min | Safe testing |
| **Total** | **4-6 hours** | Follow all steps |

---

## Success Criteria

✓ You succeed when:
1. All 14 servos respond to commands
2. Robot stands at init_pos on startup
3. Robot moves smoothly when policy runs
4. Control loop maintains 50 Hz timing
5. No error messages or crashes
6. Robot operates stably for >5 minutes
7. Gamepad control works (if enabled)
8. Robot demonstrates coordinated walking

---

## Next Steps

1. **NOW**: Print or bookmark this checklist
2. **Next**: Read README_WAVESHARE_INTEGRATION.md
3. **Then**: Follow SETUP_TESTING_GUIDE.md
4. **Check off as you progress through integration**

---

**Good luck! You've got this! 💪**

Use this checklist to track progress and ensure nothing is missed. Check off items as you complete them.

