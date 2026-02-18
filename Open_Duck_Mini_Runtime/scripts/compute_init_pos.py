import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DUCK_CONFIG = ROOT / "duck_config.json"
CALIB_PATHS = [
    Path("waveshare_calibration.json"),
    Path("stservo-env/sms_sts/waveshare_calibration.json"),
]

def find_calib():
    for p in CALIB_PATHS:
        fp = ROOT / p
        if fp.exists():
            return fp
    return None

def load_json(p):
    with open(p, "r") as f:
        return json.load(f)

def main():
    if not DUCK_CONFIG.exists():
        print(f"duck_config not found at {DUCK_CONFIG}")
        return

    calib = find_calib()
    if calib is None:
        print("Could not find waveshare_calibration.json in expected locations.")
        print("Run calibrate_waveshare.py first and place the file in the project root or stservo-env/sms_sts/")
        return

    cfg = load_json(DUCK_CONFIG)
    data = load_json(calib)

    counts_per_pi = cfg.get("counts_per_pi", 1024)
    center = counts_per_pi // 2

    joint_map = cfg.get("joint_map", {})
    init_pos = cfg.get("init_pos", {})

    # backup
    shutil.copy(DUCK_CONFIG, DUCK_CONFIG.with_suffix(".json.bak"))

    updated = 0
    for joint, sid in joint_map.items():
        # keys in calibration file might be strings
        c = None
        if str(sid) in data:
            c = data[str(sid)]
        elif sid in data:
            c = data[sid]
        if c is None:
            continue
        # compute radians
        rad = (c - center) * math.pi / (counts_per_pi / 2)
        init_pos[joint] = float(rad)
        updated += 1

    cfg["init_pos"] = init_pos
    with open(DUCK_CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)

    print(f"Updated {updated} joints in {DUCK_CONFIG}; backup saved as .json.bak")

if __name__ == "__main__":
    main()
