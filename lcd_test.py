from machine import Pin, I2C
from lcd_class import I2cLcd
import time

i2c = I2C(0, scl=Pin(20), sda=Pin(22), freq=400000)

lcd = I2cLcd(i2c, 0x27, 2, 16)

lcd.clear()
lcd.lcd_print("Hello Matt!")
time.sleep(3)
lcd.clear()


