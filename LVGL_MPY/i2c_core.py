from micropython import const
_I2C_NUM_0 = const(0)

from i2c import I2C

class I2CBUS(I2C.Bus):
    
    def __init__(self, port, scl, sda, freq = 100_000):
        self._port = port
        self._scl = scl
        self._sda = sda
        self._freq = freq
        super().__init__(host=port, scl=scl, sda=sda, freq=freq)
    def __str__(self):
        return f"I2C({self._port}, scl={self._scl}, sda={self._sda}, freq={self._freq}"

class I2CDEV():
    def __init__(self, bus, dev_id, probe_on_bus=True, reg_bits=8):
        self._bus = bus
        self._addr = dev_id
        self._reg_bits = reg_bits
        self._detected = False
        if probe_on_bus == True:
            if dev_id in bus.scan():
                self._detected = True
        
    
    def __str__(self):
        return f"I2CDevice({self._bus}, addr={self._addr:02x}, reg_addr_width={self._reg_bits}, detected={self._detected})"

    def write(self, tx_data):
        self._bus.writeto(self._addr, tx_data)
            
    def read_into(self, rx_data):
        self._bus.readfrom_into(self._addr, rx_data)
        
    def read(self, rx_len):
        rx_data = bytearray(rx_len)
        self._bus.readfrom_into(self._addr, memoryview(rx_data))
        return rx_data        
        
    def write_read_into(self, tx_data, rx_data):
        self._bus.writeto(self._addr, tx_data)
        self._bus.readfrom_into(self._addr, rx_data)
    
    def write_mem(self, regaddr, tx_data):
        self._bus.writeto_mem(self._addr, regaddr, tx_data, addrsize=self._reg_bits)
    
    def read_mem_into(self, regaddr, rx_data):
        self._bus.readfrom_mem_into(self._addr, regaddr,  rx_data, addrsize=self._reg_bits)
        
    def read_mem(self, regaddr, rx_len):
        rx_data = bytearray(rx_len)        
        self._bus.readfrom_mem_into(self._addr, regaddr, rx_data, addrsize=self._reg_bits)
        return rx_data
        
    @property
    def detected(self):
        return self._detected
