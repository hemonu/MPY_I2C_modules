import time
from i2c_core import *
from ustruct import unpack, unpack_from

START_MEASUREMENT_FLOAT = bytes.fromhex('00100300AC')
START_MEASUREMENT_INT = bytes.fromhex('00100500F6')
STOP_MEASUREMENT = bytes.fromhex('0104')
READ_DATA_READY_FLAG = bytes.fromhex('0202')
READ_MEASURED_VALUES = bytes.fromhex('0300')
SLEEP = bytes.fromhex('1001')
WAKE_UP = bytes.fromhex('1103')
START_FAN_CLEANING = bytes.fromhex('5607')
RW_AUTO_CLEANING_INTERVAL = bytes.fromhex('8004')
READ_PRODUCT_TYPE = bytes.fromhex('D002')
READ_SERIAL_NUMBER = bytes.fromhex('D033')
READ_VERSION = bytes.fromhex('D100')
READ_DEVICE_STATUS_REG = bytes.fromhex('D206')
CLEAR_DEVICE_STATUS_REG = bytes.fromhex('D210')
SOFT_RST = bytes.fromhex('D304')

SPS30_CLK_SPEED_HZ = 100_000;
SPS30_I2C_ADDRESS = 0x69;
NUMBER_OF_MEASURES = 10;

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
        
class SPS30(I2CDEV):
    # creates variables

    DATA_FORMAT_FLOAT = True;
    DATA_FORMAT_INTEGER = False;
    measures = {\
        "massPM1" : [0.0, "µg/m³", "PM1.0 Mass", "PM1.0 Masse"],\
        "massPM25" : [0.0, "µg/m³", "PM2.5 Mass", "PM2.5 Masse"],\
        "massPM4" : [0.0, "µg/m³", "PM4.0 Mass", "PM4.0 Masse"],\
        "massPM10" : [0.0, "µg/m³", "PM10 Mass", "PM10 Masse"],\
        "partPM05" : [0.0, "#/cm³", "PM0.5 Count", "PM0.5 Anzahl"],\
        "partPM1" : [0.0, "#/cm³", "PM1.0 Count", "PM1.0 Anzahl"],\
        "partPM25" : [0.0, "#/cm³", "PM2.5 Count", "PM2.5 Anzahl"],\
        "partPM4" : [0.0, "#/cm³", "PM4.0 Count", "PM4.0 Anzahl"],\
        "partPM10" : [0.0, "#/cm³", "PM10 Count", "PM10 Anzahl"],\
        "size" : [0.0, "µm", "typical size", "typische Größe"]}
    measuresValid = False
 
    def __init__(self,
                 address=SPS30_I2C_ADDRESS,
                 i2c=None,
                 **kwargs):
        self.address = address
        if i2c is None:
            raise ValueError('An I2C object is required.')
        self.i2c = i2c
        super().__init__(bus=i2c, dev_id=address, probe_on_bus=True)

    def soft_reset(self):
        self.write(SOFT_RST)
        time.sleep(0.1)
        return
    
    def get_device_type(self):
        answer = bytearray(12)
        self.write_read_into(READ_PRODUCT_TYPE, memoryview(answer))
        if chk_crc(answer):
            id = ""
            for i in range(0, len(answer), 3):
                id += answer[i:i+2].decode()
        else:
            id = None
        return id
        
    def get_device_serial(self):
        answer = bytearray(18)
        self.write_read_into(READ_SERIAL_NUMBER, memoryview(answer))
        if chk_crc(answer):
            sn = ""
            for i in range(0, len(answer), 3):
                sn += answer[i:i+2].decode()
        else:
            sn = None
        return sn
        
    def get_device_version(self):
        answer = bytearray(3)
        self.write_read_into(READ_VERSION, memoryview(answer))
        if chk_crc(answer):
            ver = ""
            major, minor = unpack(">BBx", answer)
            sn = "{}.{}".format(major, minor)
        else:
            sn = None
        return sn
        
    def get_device_status(self):
        answer = bytearray(6)
        self.write_read_into(READ_DEVICE_STATUS_REG, memoryview(answer))
        if chk_crc(answer):
            major, minor = unpack(">hxhx", answer)
            status = major << 16 + minor
        else:
            status = None
        return status
        
    def measurement_results_ready(self):
        answer = bytearray(3)
        self.write_read_into(READ_DATA_READY_FLAG, memoryview(answer))
        #print(answer.hex().upper())
        if chk_crc(answer):
            return (answer[1] == 1)
        else:
            return False
        
    def start_measurement(self):
        self.write(START_MEASUREMENT_FLOAT)
        return

    def stop_measurement(self):
        self.write(STOP_MEASUREMENT)
        return
 
    def start_fan_cleaning(self):
        self.write(START_FAN_CLEANING)
        return
    
    def ReadAllMeasures(self):
    
        '''
        reads sensor data
        checks CRC of data and
        stores calculated data into measures
        '''
        self.measuresValid = False
        answer = bytearray(60)
        self.write_read_into(READ_MEASURED_VALUES, memoryview(answer))
        #print("answer: ")
        #print(answer.hex().upper())
        if chk_crc(answer):
            data = bytearray(b'')
            for i in range(0, len(answer), 3):
                data += answer[i:i+2]
            #print("data: ")
            #print(data.hex().upper())
            i = 0
            for key in ("massPM1","massPM25","massPM4","massPM10"):
                #print(unpack_from(">f", data, i))
                self.measures[key][0] = unpack_from(">f", data, i)[0]
                i += 4
            for key in ("partPM05","partPM1","partPM25","partPM4","partPM10"):
                #print(unpack_from(">f", data, i))
                self.measures[key][0] = unpack_from(">f", data, i)[0]
                i += 4
            self.measures["size"][0] = unpack_from(">f", data, i)[0]
        return
            
 