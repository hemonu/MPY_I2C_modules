# Updated 2018 and 2020
# This module is based on the below cited resources, which are all
# based on the documentation as provided in the Bosch Data Sheet and
# the sample implementation provided therein.
#
# Final Document: BST-BME280-DS002-15
#
# Authors: Paul Cunnane 2016, Peter Dahlebrg 2016
#
# This module borrows from the Adafruit BME280 Python library. Original
# Copyright notices are reproduced below.
#
# Those libraries were written for the Raspberry Pi. This modification is
# intended for the MicroPython and esp8266 boards.
#
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Based on the BMP280 driver with BME280 changes provided by
# David J Taylor, Edinburgh (www.satsignal.eu)
#
# Based on Adafruit_I2C.py created by Kevin Townsend.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import time
from ustruct import unpack, unpack_from
from array import array
from math import exp, log

# BME280 default address.
BME280_I2CADDR = 0x76

# Operating Modes
BME280_OSAMPLE_1 = 1
BME280_OSAMPLE_2 = 2
BME280_OSAMPLE_4 = 3
BME280_OSAMPLE_8 = 4
BME280_OSAMPLE_16 = 5

BME280_REGISTER_CONTROL_HUM = 0xF2
BME280_REGISTER_STATUS = 0xF3
BME280_REGISTER_CONTROL = 0xF4

MODE_SLEEP = const(0)
MODE_FORCED = const(1)
MODE_NORMAL = const(3)

BME280_TIMEOUT = const(100)  # about 1 second timeout

class BME280:
    # creates variables
    measures = {\
        "temp" : [0.0, "°C", "Temperature", "Temperatur"],\
        "pres" : [0.0, "hPa", "Pressure", "Luftdruck"],\
        "humi" : [0.0, "%", "Humidity", "Luftfeuchte"],\
        "dewp" : [0.0, "°C", "Dew Point", "Taupunkt"],\
        "dens" : [0.0, "kg/m³", "Density", "Luftdichte"]}
    measuresValid = False
 
    def __init__(self,
                 mode=BME280_OSAMPLE_8,
                 address=BME280_I2CADDR,
                 i2c=None,
                 altitude=0,
                 **kwargs):
        # Check that mode is valid.
        if type(mode) is tuple and len(mode) == 3:
            self._mode_hum, self._mode_temp, self._mode_press = mode
        elif type(mode) == int:
            self._mode_hum, self._mode_temp, self._mode_press = mode, mode, mode
        else:
            raise ValueError("Wrong type for the mode parameter, must be int or a 3 element tuple")

        for mode in (self._mode_hum, self._mode_temp, self._mode_press):
            if mode not in [BME280_OSAMPLE_1, BME280_OSAMPLE_2, BME280_OSAMPLE_4,
                            BME280_OSAMPLE_8, BME280_OSAMPLE_16]:
                raise ValueError(
                    'Unexpected mode value {0}. Set mode to one of '
                    'BME280_OSAMPLE_1, BME280_OSAMPLE_2, BME280_OSAMPLE_4, '
                    'BME280_OSAMPLE_8 or BME280_OSAMPLE_16'.format(mode))

        self.address = address
        if i2c is None:
            raise ValueError('An I2C object is required.')
        self.i2c = i2c
        self.__altitude = altitude

        # load calibration data
        dig_88_a1 = self.i2c.readfrom_mem(self.address, 0x88, 26)
        dig_e1_e7 = self.i2c.readfrom_mem(self.address, 0xE1, 7)

        self.dig_T1, self.dig_T2, self.dig_T3, self.dig_P1, \
            self.dig_P2, self.dig_P3, self.dig_P4, self.dig_P5, \
            self.dig_P6, self.dig_P7, self.dig_P8, self.dig_P9, \
            _, self.dig_H1 = unpack("<HhhHhhhhhhhhBB", dig_88_a1)

        self.dig_H2, self.dig_H3, self.dig_H4,\
            self.dig_H5, self.dig_H6 = unpack("<hBbhb", dig_e1_e7)
        # unfold H4, H5, keeping care of a potential sign
        self.dig_H4 = (self.dig_H4 * 16) + (self.dig_H5 & 0xF)
        self.dig_H5 //= 16

        # temporary data holders which stay allocated
        self._l1_barray = bytearray(1)
        self._l8_barray = bytearray(8)
        self._l3_resultarray = array("i", [0, 0, 0])

        self._l1_barray[0] = self._mode_temp << 5 | self._mode_press << 2 | MODE_SLEEP
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL,
                             self._l1_barray)
        self.t_fine = 0

    def read_raw_data(self, result):
        """ Reads the raw (uncompensated) data from the sensor.

            Args:
                result: array of length 3 or alike where the result will be
                stored, in temperature, pressure, humidity order
            Returns:
                None
        """

        self._l1_barray[0] = self._mode_hum
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL_HUM,
                             self._l1_barray)
        self._l1_barray[0] = self._mode_temp << 5 | self._mode_press << 2 | MODE_FORCED
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL,
                             self._l1_barray)

        # wait up to about 5 ms for the conversion to start
        for _ in range(5):
            if self.i2c.readfrom_mem(self.address, BME280_REGISTER_STATUS, 1)[0] & 0x08:
                break;  # The conversion is started.
            time.sleep_ms(1)  # still not busy
        # Wait for conversion to complete
        for _ in range(BME280_TIMEOUT):
            if self.i2c.readfrom_mem(self.address, BME280_REGISTER_STATUS, 1)[0] & 0x08:
                time.sleep_ms(10)  # still busy
            else:
                break  # Sensor ready
        else:
            raise RuntimeError("Sensor BME280 not ready")

        # burst readout from 0xF7 to 0xFE, recommended by datasheet
        self.i2c.readfrom_mem_into(self.address, 0xF7, self._l8_barray)
        readout = self._l8_barray
        # pressure(0xF7): ((msb << 16) | (lsb << 8) | xlsb) >> 4
        raw_press = ((readout[0] << 16) | (readout[1] << 8) | readout[2]) >> 4
        # temperature(0xFA): ((msb << 16) | (lsb << 8) | xlsb) >> 4
        raw_temp = ((readout[3] << 16) | (readout[4] << 8) | readout[5]) >> 4
        # humidity(0xFD): (msb << 8) | lsb
        raw_hum = (readout[6] << 8) | readout[7]

        result[0] = raw_temp
        result[1] = raw_press
        result[2] = raw_hum

    def ReadAllMeasures(self):
        """ Reads the data from the sensor and returns the compensated data.

            Args:
                result: array of length 5 or alike where the result will be
                stored, in temperature, pressure, humidity, dew point, density
                order. You may use this to read out the sensor without
                allocating heap memory

            Returns:
                array with temperature, pressure, humidity, dew point, density.
                Will be the one from the result parameter if not None
        """
        self.read_raw_data(self._l3_resultarray)
        raw_temp, raw_press, raw_hum = self._l3_resultarray
        # temperature
        var1 = (raw_temp/16384.0 - self.dig_T1/1024.0) * self.dig_T2
        var2 = raw_temp/131072.0 - self.dig_T1/8192.0
        var2 = var2 * var2 * self.dig_T3
        self.t_fine = int(var1 + var2)
        temp = (var1 + var2) / 5120.0
        temp = max(-40, min(85, temp))

        # pressure
        var1 = (self.t_fine/2.0) - 64000.0
        var2 = var1 * var1 * self.dig_P6 / 32768.0 + var1 * self.dig_P5 * 2.0
        var2 = (var2 / 4.0) + (self.dig_P4 * 65536.0)
        var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.dig_P1
        if (var1 == 0.0):
            pressure = 30000  # avoid exception caused by division by zero
        else:
            p = ((1048576.0 - raw_press) - (var2 / 4096.0)) * 6250.0 / var1
            var1 = self.dig_P9 * p * p / 2147483648.0
            var2 = p * self.dig_P8 / 32768.0
            pressure = p + (var1 + var2 + self.dig_P7) / 16.0
            pressure = max(30000, min(110000, pressure))

        # humidity
        h = (self.t_fine - 76800.0)
        h = ((raw_hum - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.0 * h)) *
             (self.dig_H2 / 65536.0 * (1.0 + self.dig_H6 / 67108864.0 * h *
                                       (1.0 + self.dig_H3 / 67108864.0 * h))))
        humidity = h * (1.0 - self.dig_H1 * h / 524288.0)
        if (humidity < 0):
            humidity = 0
        if (humidity > 100):
            humidity = 100.0
            

        self.measures["temp"][0] = temp
        self.measures["humi"][0] = humidity
        self.measures["pres"][0] = (pressure / 100)
        self.measuresValid = True
        self.measures["dewp"][0] = self.dew_point
        self.measures["dens"][0] = self.density
        
        return array("f", (temp, pressure, humidity, self.measures["dewp"][0], self.measures["dens"][0]))

    @property
    def altitude(self):
        return self.__altitude

    @altitude.setter
    def altitude(self, value):
        self.__altitude = 1.0 * value #save as float

    @property
    def qnh(self):
        '''
        QNH in hPa.
        '''
        t = self.measures["temp"][0]
        p = self.measures["pres"][0]
        h = self.measures["humi"][0]
        d = self.measures["dens"][0]
        dh = self.__altitude
        e_s = 6.112 * exp(17.62 * t / (243.12 + t))
        e = e_s * h / 100.0
        t_v = (t + 273.15) / (1.0 - e / (p * 100) * (1 - 0.62197))
        q = p * exp((9.80665 * dh) / (287.05 * (t_v))) 
        return q

    @property
    def temperature(self):
        """
        Temperature
        """
        if self.measuresValid:
            return self.measures["temp"][0]
        else:
            return None

    @property
    def pressure(self):
        """
        Pressure
        """
        if self.measuresValid:
            return self.measures["pres"][0]
        else:
            return None

    @property
    def humidity(self):
        """
        Humidity
        """
        if self.measuresValid:
            return self.measures["humi"][0]
        else:
            return None

    @property
    def dew_point(self):
        """
        Compute the dew point temperature for the current Temperature
        and Humidity measured pair
        """
        if not self.measuresValid:
            return None
        h = (log(self.measures["humi"][0], 10) - 2) / 0.4343 + \
            (17.62 * self.measures["temp"][0]) / \
            (243.12 + self.measures["temp"][0])
        return 243.12 * h / (17.62 - h)

    @property
    def density(self):
        """
        Compute air density for the current Temperature, Humidity
        and Presssure
        """
        if not self.measuresValid:
            return None
        Rs = 287.058
        Rd = 461.523
        t = self.measures["temp"][0]
        p = self.measures["pres"][0]
        h = self.measures["humi"][0]
        steamPressure = 6.112 * exp(17.62 * t / (243.12 + t))
        Rf = Rs / (1.0 - h/100.0 * steamPressure / p * (1.0 - Rs/Rd))
        return p * 100.0 / (Rf * (t + 273.15))
        
    @property
    def values(self):
        """ human readable values """

        t, p, h, dp, d = self.ReadAllMeasures()

        return ("{:.2f}°C".format(t), "{:.2f}hPa".format(p/100),
                "{:.2f}%".format(h), "{:.2f}°C".format(dp), "{:.2f}kg/m³".format(d))