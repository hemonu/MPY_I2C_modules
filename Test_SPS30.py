from i2c_core import I2CDEV, I2CBUS
from time import sleep

from board import HW_DEFS
hw = HW_DEFS()

i2c0 = I2CBUS(hw.PORT, scl=hw.SCL, sda=hw.SDA, freq=100_000)

print(i2c0)

from SPS30 import *

sps = SPS30(i2c=i2c0)

sps.soft_reset()

print(" ID:", sps.get_device_type())

print("S/N:", sps.get_device_serial())

print("FW version:", sps.get_device_version())

print("Status:", "{:08x}".format(sps.get_device_status()))

#print("Measurement Ready: ", sps.measurement_results_ready())

sps.start_measurement()

for i in range(100):
    sleep(10)
    while not sps.measurement_results_ready():
        sleep(0.1)
    print("Messung", i)
    #print("Measurement Ready: ", sps.measurement_results_ready())
    sps.ReadAllMeasures()
    prior = 0.0
    for key in ("massPM1","massPM25","massPM4","massPM10"):
        print("  {:<12}: {:8.3f} {}   {:8.3f} {}".format(sps.measures[key][3], \
                        sps.measures[key][0], sps.measures[key][1], \
                        sps.measures[key][0] - prior, sps.measures[key][1]))
        prior = sps.measures[key][0]
'''
for key in ("partPM05","partPM1","partPM25","partPM4","partPM10"):
        print("{}: {:8.3f} {}".format(sps.measures[key][3], sps.measures[key][0], sps.measures[key][1]))
    key = "size"
    print("{}: {:8.3f} {}".format(sps.measures[key][3], sps.measures[key][0], sps.measures[key][1]))
'''
sps.stop_measurement()
sleep(2)

print("done")
