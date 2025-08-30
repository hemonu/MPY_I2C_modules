from i2c_core import I2CBUS, I2CDEV
#from machine import I2C

i2c0 = I2CBUS(port=0, scl=39, sda=38, freq=100_000)
#i2c0 = I2C(0, scl=39, sda=38, freq=100_000)
#print(i2c0)

from BME280 import *
from utime import sleep

bme280 = BME280(i2c=i2c0, altitude=54.0)

#bme280 = I2CDEV(bus=i2c0, dev_id=0x76, probe_on_bus=True, reg_bits=8)
#print(bme280)

#print(bme280.values)
bme280.ReadAllMeasures()
#print("Temperatur: {:.01f} °C".format(bme280.temperature))
#print("Luftdruck: {:.01f} °C".format(bme280.pressure))
#print("Feuchte: {:.01f} %".format(bme280.humidity))
#print("Taupunkt: {:.01f} °C".format(bme280.dew_point))
#print("Luftdichte: {:.04f} kg/m³".format(bme280.density))
for y in bme280.measures.values():
    print("{}: {:.02f}".format(y[3], y[0]), y[1])
print("Höhe: {:.01f} m".format(bme280.altitude))
print("QNH: {:.02f} hPa".format(bme280.qnh))
    
#buf = bytearray(26)
#bme280.receive_reg(regaddr=0x88, rx_data=memoryview(buf), rx_len=26)
#print(buf)
          