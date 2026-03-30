import machine
from machine import Pin
from machine import ADC
from machine import PWM

##############GPIO SETUP##############
led_board = Pin(13, Pin.OUT)
red_led = Pin(12, Pin.OUT)
green_led = Pin(27, Pin.OUT)
yellow_led = Pin(33, Pin.OUT)

red_button = Pin(19, Pin.IN, Pin.PULL_DOWN)
green_button = Pin(5, Pin.IN, Pin.PULL_DOWN)
yellow_button = Pin(4, Pin.IN, Pin.PULL_DOWN)

pot = ADC(Pin(34, Pin.IN))

pwm_speaker = PWM(Pin(32), freq=10, duty_u16=512) 

##########COMMON FUNCTIONS##########

def set_led(color):
    if color == "red":
        red_led.value(1)
        green_led.value(0)
        yellow_led.value(0)
    elif color == "green":
        red_led.value(0)
        green_led.value(1)
        yellow_led.value(0)
    elif color == "yellow":
        red_led.value(0)
        green_led.value(0)
        yellow_led.value(1)


##########SERVER CONFIGURATION#########


###############wAVELENGTH##############


###############MEMORY GAME#############


##########ROCK PAPER SCISSORS##########




##########MAIN LOOP##########

while True:
    pass
