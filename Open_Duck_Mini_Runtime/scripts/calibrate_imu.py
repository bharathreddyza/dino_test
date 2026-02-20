
from mini_bdx_runtime.raw_imu2 import Imu

if __name__ == "__main__":
    imu = Imu(50, calibrate=True, upside_down=True)