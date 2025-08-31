from i2c_core import I2CDEV, I2CBUS
from time import sleep
from pca9548 import *

from board import HW_DEFS
hw = HW_DEFS()

i2c0 = I2CBUS(hw.PORT, scl=hw.SCL, sda=hw.SDA, freq=100_000)

print(i2c0)

i2cmux = PCA9548(i2c=i2c0)

for i in range(9):
    i2cmux.enable(i)
    sleep(0.1)
    print(i, i2c0.scan())

i2cmux.disable()
sleep(0.1)
print ("d", i2c0.scan())
