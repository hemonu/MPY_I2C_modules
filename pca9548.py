from i2c_core import I2CDEV

PCA9548_I2C_ADDRESS = 0x70

class PCA9548(I2CDEV):
    def __init__(self,
            address=PCA9548_I2C_ADDRESS,
            i2c=None,
            **kwargs):
        self.address = address
        if i2c is None:
            raise ValueError('An I2C object is required.')
        self.i2c = i2c
        super().__init__(bus=i2c, dev_id=address, probe_on_bus=True)

    def enable(self, channel):
        if (channel <= 8) and (channel > 0):
            self.write((1 << (channel-1)).to_bytes(1))
        else:
            self.write(b'\00')
        return
    
    def disable(self):
        self.write(b'\00')
        return
