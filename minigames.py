import machine
from machine import Pin
from machine import ADC
from machine import PWM

led_board = Pin(13, Pin.OUT)
red_led = Pin(12, Pin.OUT)
green_led = Pin(27, Pin.OUT)
yellow_led = Pin(33, Pin.OUT)

red_button = Pin(19, Pin.IN, Pin.PULL_DOWN)
green_button = Pin(5, Pin.IN, Pin.PULL_DOWN)
yellow_button = Pin(4, Pin.IN, Pin.PULL_DOWN)

pot = ADC(Pin(34, Pin.IN))

pwm_speaker = PWM(Pin(32), freq=10, duty_u16=512) 

