# Waveshare Servo Integration - Document Index

## Quick Navigation

### 🚀 **START HERE**
- [README_WAVESHARE_INTEGRATION.md](README_WAVESHARE_INTEGRATION.md) - Overview and quick start (5 min read)

### 📚 **Understanding the System**
1. [VISUAL_GUIDE.md](VISUAL_GUIDE.md) - Diagrams and flowcharts
2. [WAVESHARE_ADAPTATION_GUIDE.md](WAVESHARE_ADAPTATION_GUIDE.md) - Technical deep-dive
3. [COMPARISON_MIGRATION_REFERENCE.md](COMPARISON_MIGRATION_REFERENCE.md) - Feetech vs Waveshare comparison

### 🔧 **Implementation**
1. [SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md) - Step-by-step setup
2. [waveshare_position_hwi.py](mini_bdx_runtime/mini_bdx_runtime/waveshare_position_hwi.py) - Hardware adapter code
3. [test_waveshare_setup.py](test_waveshare_setup.py) - Diagnostic tests

### 📖 **Reference**
- Servo datasheet (not included - get from Waveshare)
- duck_config.json (your robot configuration)
- policy.onnx (trained RL model)

---

## Document Descriptions

### README_WAVESHARE_INTEGRATION.md
**What it is**: Executive summary and quick start guide
**Length**: ~30 min read
**Contains**:
- What you got (5 new files)
- How it works (30-second overview)
- Quick start (5 minutes)
- Architecture overview
- Key concepts
- File modifications needed
- Testing sequence
- Troubleshooting flowchart
- Performance tuning

**Read this first if you want**: Quick overview and to get started immediately

---

### VISUAL_GUIDE.md
**What it is**: Diagrams, flowcharts, and visual architecture
**Length**: ~15 min read with diagrams
**Contains**:
- System architecture diagram
- Data flow (sensors → policy → servos)
- Robot startup sequence
- Control timing (50 Hz loop)
- Joint configuration map
- Unit conversion table
- Numpy array shapes and types
- Debugging print statements
- Success indicators

**Read this if you want**: To see how everything fits together visually

---

### WAVESHARE_ADAPTATION_GUIDE.md
**What it is**: Complete technical documentation
**Length**: ~45 min read
**Contains**:
- RL Policy overview and control flow
- High-level architecture explanation
- Key code locations
- Data flow (sensors to motors)
- Observation vector assembly (125 dimensions)
- Action output processing
- Hardware Interface (HWI) explanation
- Feetech vs Waveshare protocol comparison
- Implementation strategy
- Usage instructions (switching imports)
- Calibration procedures
- Tuning guide (speed, acceleration, KP/KD)
- Troubleshooting by issue type

**Read this if you want**: Deep understanding of how everything works

---

### SETUP_TESTING_GUIDE.md
**What it is**: Practical step-by-step setup instructions
**Length**: ~30 min to implement
**Contains**:
- Quick start checklist
- Python environment setup
- Serial port identification
- Servo discovery procedure
- Position mapping calibration (step-by-step)
- Verification tests (center position, smooth movement)
- Integration with RL policy
- Complete joint configuration reference
- Troubleshooting for each step
- Performance tuning parameters
- Validation procedures

**Read this if you want**: To actually set up and test your system

---

### COMPARISON_MIGRATION_REFERENCE.md
**What it is**: Side-by-side comparison of Feetech vs Waveshare
**Length**: ~20 min read
**Contains**:
- Feetech architecture (current)
- Waveshare architecture (new)
- Data flow comparison
- Method mapping table
- Unit conversion details
- Protocol differences
- Migration checklist
- Quick reference table
- Common issues & solutions
- References & datasheets

**Read this if you want**: To understand differences from Feetech

---

### waveshare_position_hwi.py
**What it is**: Hardware Interface adapter code (replacement for rustypot_position_hwi.py)
**Language**: Python 3
**Contains**:
- WaveshareHWI class (drop-in replacement)
- Position mapping functions (rad_to_servo_pos, servo_pos_to_rad)
- Servo communication (PortHandler + sms_sts)
- All HWI interface methods:
  - set_position_all()
  - get_present_positions()
  - get_present_velocities()
  - turn_on() / turn_off()
  - set_kps() / set_kds()
  - scan_servos()
  - close()
- Servo calibration support
- Temperature & voltage reading
- Comments and docstrings

**Use this**: Copy to `mini_bdx_runtime/mini_bdx_runtime/waveshare_position_hwi.py`

---

### test_waveshare_setup.py
**What it is**: Automated diagnostic test suite
**Language**: Python 3
**Runs**: Tests without modifying robot state
**Tests included**:
1. Discovery - Find all connected servos
2. Positions - Read position from each servo
3. Speeds - Read velocity from each servo
4. Single Movement - Move one servo to target
5. All Movement - Move all servos in cycles
6. HWI Interface - Test WaveshareHWI class

**Use this**: `python test_waveshare_setup.py --port COM5 --test all`

---

## How to Use These Documents

### Scenario 1: "I want to get it working FAST"
1. Read: [README_WAVESHARE_INTEGRATION.md](README_WAVESHARE_INTEGRATION.md) (5 min)
2. Follow: [SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md#step-1-setup-python-environment) steps 1-3
3. Copy: [waveshare_position_hwi.py](mini_bdx_runtime/mini_bdx_runtime/waveshare_position_hwi.py)
4. Run: `python test_waveshare_setup.py`
5. Integrate: Update import in v2_rl_walk_mujoco.py
6. Go!

**Time**: ~30 minutes

---

### Scenario 2: "I want to understand everything"
1. Read: [VISUAL_GUIDE.md](VISUAL_GUIDE.md) (15 min)
2. Read: [WAVESHARE_ADAPTATION_GUIDE.md](WAVESHARE_ADAPTATION_GUIDE.md) (45 min)
3. Skim: [COMPARISON_MIGRATION_REFERENCE.md](COMPARISON_MIGRATION_REFERENCE.md) (10 min)
4. Study: [waveshare_position_hwi.py](mini_bdx_runtime/mini_bdx_runtime/waveshare_position_hwi.py) code (20 min)
5. Then: Follow setup guide to implement

**Time**: ~3 hours (but you'll know everything)

---

### Scenario 3: "Something's broken, help!"
1. Check: [Troubleshooting Flowchart](README_WAVESHARE_INTEGRATION.md#troubleshooting-flowchart)
2. Run: `python test_waveshare_setup.py --test <failing_test>`
3. Read: Relevant section in [SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md#step-6-troubleshooting)
4. Verify: [WAVESHARE_ADAPTATION_GUIDE.md](WAVESHARE_ADAPTATION_GUIDE.md#part-7-troubleshooting)
5. Debug: Use debugging statements from [VISUAL_GUIDE.md](VISUAL_GUIDE.md#debugging-common-print-statements)

**Time**: Depends on issue

---

### Scenario 4: "I need to calibrate the servos"
1. Follow: [SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md#step-3-calibrate-position-mapping)
2. Use: The calibration script provided
3. Update: [waveshare_position_hwi.py](mini_bdx_runtime/mini_bdx_runtime/waveshare_position_hwi.py) methods:
   - `rad_to_servo_pos()`
   - `servo_pos_to_rad()`
4. Validate: `python test_waveshare_setup.py --test single`

**Time**: ~1-2 hours for all 14 servos

---

## File Organization in Your Workspace

```
STServo_Python/
└── Open_Duck_Mini_Runtime/
    ├── mini_bdx_runtime/
    │   └── mini_bdx_runtime/
    │       ├── rustypot_position_hwi.py    (original - kept)
    │       └── waveshare_position_hwi.py   (NEW - copy here)
    │
    ├── scripts/
    │   └── v2_rl_walk_mujoco.py            (MODIFY: 1 import line)
    │
    ├── README_WAVESHARE_INTEGRATION.md     (START HERE)
    ├── VISUAL_GUIDE.md                     (Diagrams)
    ├── WAVESHARE_ADAPTATION_GUIDE.md       (Technical details)
    ├── SETUP_TESTING_GUIDE.md              (Step-by-step)
    ├── COMPARISON_MIGRATION_REFERENCE.md   (Feetech vs WX)
    │
    └── test_waveshare_setup.py             (Run tests here)
```

---

## Quick Command Reference

### Discover Servos
```bash
python test_waveshare_setup.py --port COM5 --test discovery
```

### Test All Servos
```bash
python test_waveshare_setup.py --port COM5 --test all
```

### Test Single Servo
```bash
python test_waveshare_setup.py --port COM5 --test single --servo-id 10 --position 1024
```

### Test HWI Class
```bash
python test_waveshare_setup.py --port COM5 --test hwi
```

### Run Full RL Policy
```bash
python scripts/v2_rl_walk_mujoco.py \
    --onnx_model_path="path/to/policy.onnx" \
    --duck_config_path="path/to/duck_config.json"
```

---

## Key Implementation Steps

### 1. Copy Hardware Adapter
```bash
cp waveshare_position_hwi.py \
   mini_bdx_runtime/mini_bdx_runtime/waveshare_position_hwi.py
```

### 2. Update Import
In `scripts/v2_rl_walk_mujoco.py`, line 6:
```python
# FROM:
from mini_bdx_runtime.rustypot_position_hwi import HWI

# TO:
from mini_bdx_runtime.waveshare_position_hwi import WaveshareHWI as HWI
```

### 3. Calibrate Position Mapping
Edit `waveshare_position_hwi.py`, method `rad_to_servo_pos()`:
```python
def rad_to_servo_pos(self, rad):
    # CUSTOMIZE for your servo mounts
    servo_pos = (rad / np.pi) * 1024 + 1024
    return np.clip(servo_pos, 0, 2047)
```

### 4. Run Tests
```bash
python test_waveshare_setup.py --port COM5 --test all
```

### 5. Deploy
```bash
python scripts/v2_rl_walk_mujoco.py --onnx_model_path=...
```

---

## Common Tasks & Where to Find Help

| Task | Document | Section |
|------|----------|---------|
| Get started quickly | README_WAVESHARE_INTEGRATION | Quick Start |
| Understand architecture | VISUAL_GUIDE | Overview Diagram |
| Learn RL policy | WAVESHARE_ADAPTATION_GUIDE | Part 1-2 |
| Setup environment | SETUP_TESTING_GUIDE | Step 1-2 |
| Find servo IDs | SETUP_TESTING_GUIDE | Step 2 |
| Calibrate positions | SETUP_TESTING_GUIDE | Step 3 |
| Test servos | test_waveshare_setup.py | --help |
| Integrate with RLWalk | SETUP_TESTING_GUIDE | Step 5 |
| Understand differences | COMPARISON_MIGRATION_REFERENCE | All sections |
| Debug issues | SETUP_TESTING_GUIDE | Step 6 |
| Understand protocols | WAVESHARE_ADAPTATION_GUIDE | Part 3-4 |
| Tune performance | SETUP_TESTING_GUIDE | Step 7 |
| See data flows | VISUAL_GUIDE | Data Flow section |
| Understand joints | VISUAL_GUIDE | Joint Configuration |
| Learn conversions | VISUAL_GUIDE | Unit Conversions |

---

## Success Checklist

Once you complete integration, verify:

- [ ] All 14 servos detected with correct IDs
- [ ] Position mapping calibrated per servo
- [ ] Robot stands at init_pos when powered on
- [ ] Servos move smoothly in test_waveshare_setup.py
- [ ] RLWalk initializes without errors
- [ ] Observation vector is 125 dimensions
- [ ] Policy runs at ~50 Hz (20ms cycles)
- [ ] Robot moves legs when policy runs
- [ ] Gamepad commands work (if enabled)
- [ ] CPU usage is 20-40%
- [ ] No NaN or timeout errors in logs

---

## Support & Contact

If you encounter issues:

1. **Read the troubleshooting guide** first
   - [SETUP_TESTING_GUIDE.md - Troubleshooting](SETUP_TESTING_GUIDE.md#step-6-troubleshooting)

2. **Run diagnostic tests**
   ```bash
   python test_waveshare_setup.py --test all
   ```

3. **Check the comparison guide**
   - [COMPARISON_MIGRATION_REFERENCE.md - Common Issues](COMPARISON_MIGRATION_REFERENCE.md#troubleshooting)

4. **Review your servo datasheet**
   - Register addresses may differ
   - Position ranges may vary

5. **Check motor calibration**
   - Position mapping is the most likely source of issues
   - Use test_waveshare_setup.py --test single to verify

---

## Next Steps

1. **Read**: [README_WAVESHARE_INTEGRATION.md](README_WAVESHARE_INTEGRATION.md) (5 min)
2. **Setup**: Follow [SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md) (30 min)
3. **Test**: Run `python test_waveshare_setup.py --port COM5 --test all` (5 min)
4. **Deploy**: Update your v2_rl_walk_mujoco.py import (1 min)
5. **Walk**: Watch your robot walk! 🚀

---

**Good luck! You've got this! 💪**

All the documentation and code you need is here. Start with README_WAVESHARE_INTEGRATION.md and follow from there.

