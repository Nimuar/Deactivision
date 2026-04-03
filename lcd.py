import machine

class LCD_I2C:
    def __init__(self, i2c, address=0x27, cols=16, rows=2):
        self.i2c = i2c
        self.address = address
        self.cols = cols
        self.rows = rows
        self.init_lcd()
    
    def init_lcd(self):
        """Initialize the LCD"""
        self.write_cmd(0x33)
        self.write_cmd(0x32)
        self.write_cmd(0x28)
        self.write_cmd(0x0C)
        self.write_cmd(0x06)
        self.write_cmd(0x01)
        machine.Timer(0).init(period=50, mode=machine.Timer.ONE_SHOT, callback=lambda t: None)
    
    def write_cmd(self, cmd):
        """Write command to LCD"""
        self.i2c.writeto(self.address, bytes([cmd]))
    
    def write_data(self, data):
        """Write data to LCD"""
        self.i2c.writeto(self.address, bytes([data | 0x80]))
    
    def print(self, text):
        """Print text to LCD"""
        self.write_cmd(0x01)  # Clear display
        for i, char in enumerate(text):
            if i < self.cols:
                self.write_data(ord(char))