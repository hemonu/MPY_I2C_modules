from i2c_core import I2CBUS, I2CDEV
from time import sleep

from board import HW_DEFS
hw = HW_DEFS()

i2c0 = I2CBUS(hw.PORT, scl=hw.SCL, sda=hw.SDA, freq=100_000)

print(i2c0)


from sdp8XX import *

airspeed = SDP8XX(i2c=i2c0)

airspeed.soft_reset()

print(" ID:", airspeed.get_device_type())

print("S/N:", airspeed.get_device_serial())

airspeed.start_cont_meas(mode=airspeed.MODE_DP, averaging=True)

for i in range(10):
    sleep(1)
    airspeed.ReadAllMeasures()
    for y in airspeed.measures.values():
        print("{:15}: {:4.2f} {}".format(y[3], y[0], y[1]))
    print(airspeed.values)