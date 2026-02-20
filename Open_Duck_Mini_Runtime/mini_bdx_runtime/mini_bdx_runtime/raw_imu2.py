# raw_imu.py
# Raspberry Pi + BNO085 UART-RVC test

import time
import serial
import numpy as np
from adafruit_bno08x_rvc import BNO08x_RVC


class Imu:
    def __init__(self, sampling_freq=50):
        self.sampling_freq = sampling_freq

        # Open Raspberry Pi hardware UART
        self.uart = serial.Serial("/dev/serial0", 115200, timeout=1)

        # Initialize RVC mode driver
        self.imu = BNO08x_RVC(self.uart)

    def read(self):
        yaw, pitch, roll, x_accel, y_accel, z_accel = self.imu.heading

        return {
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
            "gyro": [0, 0, 0],  # RVC mode does NOT provide gyro
            "accelero": [x_accel, y_accel, z_accel],
        }


if __name__ == "__main__":
    imu = Imu(50)

    while True:
        try:
            data = imu.read()
            print("Yaw:", round(data["yaw"], 2),
                  "Pitch:", round(data["pitch"], 2),
                  "Roll:", round(data["roll"], 2))
            print("Accel:", np.around(data["accelero"], 3))
            print("----")
        except Exception as e:
            print("IMU Error:", e)

        time.sleep(0.1)