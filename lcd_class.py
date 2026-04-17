from machine import Pin, I2C
import time


class I2cLcd:
    LCD_CLR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x04
    LCD_ENTRY_INC = 0x02
    LCD_ON_CTRL = 0x08
    LCD_ON_DISPLAY = 0x04
    LCD_FUNCTION = 0x20
    LCD_FUNCTION_2LINES = 0x08

    ENABLE = 0x04
    BACKLIGHT = 0x08

    def __init__(self, i2c, addr=0x27, rows=2, cols=16):
        self.i2c = i2c
        self.addr = addr
        self.rows = rows
        self.cols = cols

        time.sleep_ms(20)
        self._cmd(0x33)
        self._cmd(0x32)
        self._cmd(self.LCD_FUNCTION | self.LCD_FUNCTION_2LINES)
        self._cmd(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)
        self._cmd(self.LCD_ENTRY_MODE | self.LCD_ENTRY_INC)
        self.clear()

    def _cmd(self, cmd):
        self._write(cmd, 0)

    def _data(self, data):
        self._write(data, 1)

    def _write(self, val, mode):
        high = mode | (val & 0xF0) | self.BACKLIGHT
        low  = mode | ((val << 4) & 0xF0) | self.BACKLIGHT

        self.i2c.writeto(self.addr, bytes([high | self.ENABLE]))
        self.i2c.writeto(self.addr, bytes([high & ~self.ENABLE]))
        self.i2c.writeto(self.addr, bytes([low | self.ENABLE]))
        self.i2c.writeto(self.addr, bytes([low & ~self.ENABLE]))

    def clear(self):
        self._cmd(self.LCD_CLR)
        time.sleep_ms(2)

    def lcd_print(self, string):
        for char in string:
            self._data(ord(char))

