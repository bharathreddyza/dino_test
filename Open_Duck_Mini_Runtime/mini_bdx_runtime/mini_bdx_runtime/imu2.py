"""
imu.py — Read orientation & acceleration from BNO085 via UART
"""

import time
import board
import busio

from adafruit_bno08x_rvc import BNO08x_RVC

class IMU:
    def __init__(self, uart_port=None, baudrate=115200):
        """
        Initialize the IMU over UART.
        """
        # If using CircuitPython-style busio:
        self.uart = busio.UART(board.TX, board.RX, baudrate=baudrate, receiver_buffer_size=2048)

        # If using Raspberry Pi Python with pyserial, comment out above and
        # uncomment below:
        # import serial
        # self.uart = serial.Serial(uart_port or "/dev/serial0", baudrate)

        self._sensor = BNO08x_RVC(self.uart)

    def read(self):
        """
        Returns yaw, pitch, roll (degrees) + acceleration (m/s^2).
        """
        yaw, pitch, roll, x_accel, y_accel, z_accel = self._sensor.heading
        return {
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
            "accel": (x_accel, y_accel, z_accel),
        }

if __name__ == "__main__":
    imu = IMU()
    while True:
        data = imu.read()
        print(f"Yaw: {data['yaw']:.2f}, Pitch: {data['pitch']:.2f}, Roll: {data['roll']:.2f}")
        print(f"Acceleration: X={data['accel'][0]:.2f} Y={data['accel'][1]:.2f} Z={data['accel'][2]:.2f}")
        time.sleep(0.1)