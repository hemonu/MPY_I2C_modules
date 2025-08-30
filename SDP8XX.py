import time
from ustruct import unpack, unpack_from
from array import array
from math import exp, log

# BME280 default address.
SDP810_I2CADDR = 0x25
SDP811_I2CADDR = 0x26

# Commands
HUM_LSB = 0xFE;
START_CONT_MEAS_MASS_AVG = bytes.fromhex('3603')
START_CONT_MEAS_MASS_SNGL = bytes.fromhex('3608')
START_CONT_MEAS_DP_AVG = bytes.fromhex('3615')
START_CONT_MEAS_DP_SNGL = bytes.fromhex('361E')
STOP_CONT_MEAS = bytes.fromhex('3FF9')
START_TRIG_MEAS_MASS = bytes.fromhex('3624')
START_TRIG_MEAS_MASS_CLKSTR = bytes.fromhex('3726')
START_TRIG_MEAS_DP = bytes.fromhex('362F')
START_TRIG_MEAS_DP_CLKSTR = bytes.fromhex('372D')
SOFT_RST = bytes.fromhex('0006')
ENTER_SLEEP = bytes.fromhex('3677')
READ_ID_0 = bytes.fromhex('367C')
READ_ID_1 = bytes.fromhex('E102')

# PRODUCT ID
SDP_800_500 = '03020101'
SDP_810_500 = '03020A01'
SDP_801_500 = '03020401'
SDP_811_500 = '03020D01'
SDP_800_125 = '03020201'
SDP_810_125 = '03020B01'

SDP8XX_CLK_SPEED_HZ = 100_000

def calc_crc(data):
    '''
    calculates CRC-8 for 2 bytes
    according Sensirion SDP8XX spec
    Width: 8 bit
    Polynom: 0x31
    Init: 0xFF
    no Reflects
    Final XOR: 0x00 (none)
    '''
    crc = 0xFF
    for value in data:
        crc ^= value
        for i in range(8):
            if crc & (1 << 7):
                crc = (crc << 1) ^ 0x31
            else:
                crc = crc << 1
            crc &= (1 << 8) - 1
    return crc
    
def chk_crc(data):
    '''
    Checks if crc of data is correct
    two data bytes are followed by 1 CRC byte
    '''
    if len(data) % 3 == 0:
        crc_correct = True
        for i in range(0, len(data), 3):
            if calc_crc(data[i:i+2]) != int(data[i+2]):
                #print("{} {:02x}".format(data[i:i+3].hex(), calc_crc(data[i:i+2])))
                crc_correct = False
    else:
        #print("length:", len(data), len(data) % 3)
        crc_correct = False
    return crc_correct
        

class SDP8XX:
    # creates variables
    MODE_MASS = True;
    MODE_DP = False;
    measures = {\
        "pres" : [0.0, "Pa", "Differential Pressure", "Druckdifferenz"],\
        "temp" : [0.0, "°C", "Temperature", "Temperatur"]}
    measuresValid = False
 
    def __init__(self,
                 address=SDP810_I2CADDR,
                 i2c=None,
                 **kwargs):
        self.address = address
        if i2c is None:
            raise ValueError('An I2C object is required.')
        self.i2c = i2c

    def soft_reset(self):
        self.i2c.writeto(0, bytes.fromhex('06'))
        time.sleep(0.1)
        return
    
    def get_device_type(self):
        answer = bytearray(6)
        self.i2c.writeto(self.address, READ_ID_0)
        self.i2c.writeto(self.address, READ_ID_1)
        self.i2c.readfrom_into(self.address, memoryview(answer))
        if chk_crc(answer):
            id = answer[0:2].hex().upper() + answer[3:5].hex().upper()
        else:
            id = None
        return id
        
    def get_device_serial(self):
        answer = bytearray(18)
        self.i2c.writeto(self.address, READ_ID_0)
        self.i2c.writeto(self.address, READ_ID_1)
        self.i2c.readfrom_into(self.address, memoryview(answer))
        if chk_crc(answer):
            sn = ""
            for i in (6,9,12,15):
                sn += answer[i:i+2].hex().upper()
        else:
            sn = None
        return sn
        
    def start_cont_meas(self, mode:bool, averaging:bool):
        if mode == self.MODE_MASS:
            if averaging:
                self.i2c.writeto(self.address, START_CONT_MEAS_MASS_AVG)
            else:
                self.i2c.writeto(self.address, START_CONT_MEAS_MASS_SNGL)
        else:
            if averaging:
                self.i2c.writeto(self.address, START_CONT_MEAS_DP_AVG)
            else:
                self.i2c.writeto(self.address, START_CONT_MEAS_DP_SNGL)
        return
    
    def stop_cont_meas(self):
        self.i2c.writeto(self.address, STOP_CONT_MEAS)
        return
    
    def ReadAllMeasures(self):
    
        '''
        reads sensor data
        checks CRC of data and
        stores calculated data into measures
        '''
        self.measuresValid = False
        answer = bytearray(9)
        self.i2c.readfrom_into(self.address, memoryview(answer))
        #print(answer.hex().upper())
        if chk_crc(answer):
            p,t,s = unpack(">hxhxhx", answer)
            self.measures["pres"][0] = float(p) / s
            self.measures["temp"][0] = float(t) / 200.0
            self.measuresValid = True
        return
            
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
    def values(self):
        """ human readable values """

        if self.measuresValid:
            p = self.measures["pres"][0]
            t = self.measures["temp"][0]
            return ("{:.2f}Pa".format(p), "{:.2f}°C".format(t))
