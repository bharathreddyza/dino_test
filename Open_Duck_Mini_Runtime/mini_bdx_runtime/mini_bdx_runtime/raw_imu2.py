"""
raw_imu.py — Basic UART test for BNO085 IMU
"""

import time
import board
import busio

from adafruit_bno08x_rvc import BNO08x_RVC

def basic_uart_test():
    uart = busio.UART(board.TX, board.RX, baudrate=115200, receiver_buffer_size=2048)

    # For Raspberry Pi Python, use pyserial instead:
    # import serial
    # uart = serial.Serial("/dev/serial0", 115200)

    imu = BNO08x_RVC(uart)

    # Read a few samples
    for i in range(10):
        yaw, pitch, roll, x_a, y_a, z_a = imu.heading
        print(f"[{i}] YPR: {yaw:.2f}, {pitch:.2f}, {roll:.2f} | Accel: {x_a:.2f}, {y_a:.2f}, {z_a:.2f}")
        time.sleep(0.2)

if __name__ == "__main__":
    basic_uart_test()