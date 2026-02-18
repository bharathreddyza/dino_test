import time
import math
import json
from typing import Dict, List

from scservo_sdk import PortHandler

try:
    from scservo_sdk import scscl as scscl_module
except Exception:
    scscl_module = None

try:
    from scservo_sdk import sms_sts as sms_sts_module
except Exception:
    sms_sts_module = None


def clamp(v, a, b):
    return max(a, min(b, v))


class WaveshareHWI:
    """Minimal Waveshare HWI adapter matching rustypot HWI shape.

    - `duck_config` is expected to contain `joint_map`, `init_pos` and optionally
      `use_waveshare` and `protocol` ('scscl' or 'sms_sts').
    - Positions are converted from radians -> servo counts using a configurable
      resolution. For SC family (scscl) typical resolution is 1024 counts == 180°.
    """

    def __init__(self, duck_config, serial_port: str = "COM5", baudrate: int = 1000000):
        self.duck_config = duck_config
        self.serial_port = serial_port
        self.baudrate = baudrate

        self.protocol = getattr(duck_config, "protocol", "scscl")

        self.port = PortHandler(self.serial_port)
        self.port.openPort()
        self.port.setBaudRate(self.baudrate)

        if self.protocol == "sms_sts":
            packet_cls = sms_sts_module.sms_sts if sms_sts_module else None
        else:
            packet_cls = scscl_module.scscl if scscl_module else None

        if packet_cls is None:
            raise RuntimeError("Required scservo packet handler not available")

        self.packet = packet_cls(self.port)

        # Default resolution parameters (SC family)
        # counts_per_pi: counts that represent π radians (180°)
        self.counts_per_pi = getattr(duck_config, "counts_per_pi", 1024)

        # joint mapping & init_pos expected in duck_config
        self.joints = getattr(duck_config, "joint_map", {})
        self.init_pos = getattr(duck_config, "init_pos", {})

    def rad_to_servo_pos(self, rad: float) -> int:
        # Map radians to servo counts. rad==0 maps to center.
        center = int(self.counts_per_pi / 2)
        pos = int((rad / math.pi) * (self.counts_per_pi / 2) + center)
        return clamp(pos, 0, self.counts_per_pi - 1)

    def servo_pos_to_rad(self, count: int) -> float:
        center = int(self.counts_per_pi / 2)
        return (count - center) * math.pi / (self.counts_per_pi / 2)

    def set_kps(self, kps: List[float]):
        # Not implemented: store for compatibility
        self._kps = kps

    def set_kds(self, kds: List[float]):
        self._kds = kds

    def turn_on(self):
        # Enable torque for all known joints (if supported)
        for name, sid in self.joints.items():
            try:
                self.packet.write1ByteTxRx(sid, 24, 1)  # torque enable register (common)
            except Exception:
                pass

    def turn_off(self):
        for name, sid in self.joints.items():
            try:
                self.packet.write1ByteTxRx(sid, 24, 0)
            except Exception:
                pass

    def set_position_all(self, joints_dict: Dict[str, float], speed: int = 500, acc: int = 30):
        # joints_dict: {joint_name: rad}
        for name, rad in joints_dict.items():
            sid = self.joints.get(name)
            if sid is None:
                continue
            pos = self.rad_to_servo_pos(rad)
            if self.protocol == "sms_sts":
                # ST family
                self.packet.WritePosEx(sid, pos, speed, acc)
            else:
                # SC family: WritePos(id, position, time_ms, speed)
                # use time=0 for immediate, speed is 0-3000
                self.packet.WritePos(sid, pos, 0, speed)

    def get_present_positions(self, ignore: List[str] = None):
        ignore = ignore or []
        out = []
        for name in sorted(self.joints.keys()):
            if name in ignore:
                continue
            sid = self.joints[name]
            try:
                pos, _, _ = self.packet.ReadPos(sid)
                out.append(self.servo_pos_to_rad(pos))
            except Exception:
                out.append(0.0)
        return out

    def get_present_velocities(self, ignore: List[str] = None):
        ignore = ignore or []
        out = []
        for name in sorted(self.joints.keys()):
            if name in ignore:
                continue
            sid = self.joints[name]
            try:
                spd, _, _ = self.packet.ReadSpeed(sid)
                # conversion to rad/s is hardware-specific; leave raw scaled
                out.append(spd)
            except Exception:
                out.append(0.0)
        return out

    def scan_servos(self, id_range=range(1, 255)):
        found = []
        for sid in id_range:
            try:
                _, res, err = self.packet.ReadPos(sid)
                if res == 0:
                    found.append(sid)
            except Exception:
                pass
        return found

    def close(self):
        try:
            self.port.closePort()
        except Exception:
            pass
