# imu.py
# Raspberry Pi + BNO085 UART-RVC threaded version

import time
import serial
import numpy as np
from queue import Queue
from threading import Thread
from adafruit_bno08x_rvc import BNO08x_RVC


class Imu:
    def __init__(
        self,
        sampling_freq=50,
        user_pitch_bias=0,
        upside_down=True,
    ):
        self.sampling_freq = sampling_freq
        self.user_pitch_bias = user_pitch_bias
        self.upside_down = upside_down

        # Open hardware UART
        self.uart = serial.Serial("/dev/serial0", 115200, timeout=1)

        # Create IMU instance
        self.imu = BNO08x_RVC(self.uart)

        self.last_imu_data = {
            "yaw": 0,
            "pitch": 0,
            "roll": 0,
            "accelero": [0, 0, 0],
        }

        self.imu_queue = Queue(maxsize=1)

        Thread(target=self.imu_worker, daemon=True).start()

    def imu_worker(self):
        while True:
            start = time.time()

            try:
                yaw, pitch, roll, x_accel, y_accel, z_accel = self.imu.heading

                # Apply pitch bias
                pitch -= self.user_pitch_bias

                if self.upside_down:
                    pitch = -pitch
                    roll = -roll

                data = {
                    "yaw": yaw,
                    "pitch": pitch,
                    "roll": roll,
                    "accelero": [x_accel, y_accel, z_accel],
                }

                if self.imu_queue.full():
                    self.imu_queue.get()

                self.imu_queue.put(data)

            except Exception as e:
                print("[IMU ERROR]:", e)

            elapsed = time.time() - start
            time.sleep(max(0, 1 / self.sampling_freq - elapsed))

    def get_data(self):
        try:
            self.last_imu_data = self.imu_queue.get(False)
        except:
            pass

        return self.last_imu_data


if __name__ == "__main__":
    imu = Imu(50)

    while True:
        data = imu.get_data()
        print(
            f"Yaw: {data['yaw']:.2f}, "
            f"Pitch: {data['pitch']:.2f}, "
            f"Roll: {data['roll']:.2f}"
        )
        print("Accel:", np.around(data["accelero"], 3))
        print("----")
        time.sleep(0.1)