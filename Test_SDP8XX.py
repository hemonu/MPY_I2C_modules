from i2c_core import I2CBUS, I2CDEV
from time import sleep
#from machine import I2C

i2c0 = I2CBUS(port=0, scl=39, sda=38, freq=100_000)
#i2c0 = I2C(0, scl=39, sda=38, freq=100_000)
print(i2c0)

'''
answer = bytearray(18)

i2c0.writeto(0x25, b'\x36\x7C')

i2c0.writeto(0x25, b'\xE1\x02')

i2c0.readfrom_into(0x25, memoryview(answer))

print(answer.hex())

id = answer[0:2].hex().upper() + answer[3:5].hex().upper()

sn = ''

for i in (6,9,12,15):
    sn = sn + answer[i:i+2].hex().upper()

print(" ID:", id)

print("S/N:", sn)

'''
from SDP8XX import *

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