from timeit import Timer

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
red_button_cnt = 0
green_button_cnt = 0
yellow_button_cnt = 0

button_timer = Timer(0)
pot_timer = Timer(1)
wavelength_timer = Timer(2)
wave_timeout = False

pot = ADC(Pin(34, Pin.IN))
pwm_speaker = PWM(Pin(32), freq=10, duty_u16=512) 

game = "none"
role = "none"

##########COMMON FUNCTIONS##########

def set_led(color):
    #Can be called to set any of the LEDs by passing the color you want to turn on.
    #The other colors not passed will be turned off
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

def clear_led():
        red_led.value(0)
        green_led.value(0)
        yellow_led.value(0)


###########INTERRUPTS################   
    
def yellow_buttonpress(Pin):
    button_timer.init(period=50, mode=Timer.ONE_SHOT, callback=debounce_yellow)

def green_buttonpress(Pin):
    button_timer.init(period=50, mode=Timer.ONE_SHOT, callback=debounce_green)
    
def red_buttonpress(Pin):
    button_timer.init(period=50, mode=Timer.ONE_SHOT, callback=debounce_red)

def debounce_yellow(t):
    global yellow_button_cnt
    yellow_button_cnt = yellow_button_cnt + 1

def debounce_green(t):
    global green_button_cnt
    green_button_cnt = green_button_cnt + 1

def debounce_red(t):
    global red_button_cnt
    red_button_cnt = red_button_cnt + 1


red_button.irq(handler=red_buttonpress,trigger=Pin.IRQ_RISING)
green_button.irq(handler=green_buttonpress,trigger=Pin.IRQ_RISING)
yellow_button.irq(handler=yellow_buttonpress,trigger=Pin.IRQ_RISING)

##########SERVER CONFIGURATION#########




###############wAVELENGTH##############
def wavelength_timeout(t):
    global wave_timeout
    wave_timeout = True

def potread(t):
    global pot_val
    pot_val = pot.read()

def Wavelength_player():
    button_count = red_button_cnt + green_button_cnt + yellow_button_cnt
    Wavestate = "active"
    #Receive word/category and display as text - need help Henry/Tom
    #Start 30sec timer
    wavelength_timer.init(period=30000, mode=Timer.ONE_SHOT, callback=wavelength_timeout)
    #Display countdown on board?
    #Read POT if we need to display it, otherwise just read when timer expires or button is hit. 
    pot_timer.init(period=100, mode=Timer.PERIODIC, callback=potread)
    #Display POT(0-100%) on board as feedback?
    #IF any button is pressed, or if 30sec timer expires then save and submit POT
    while Wavestate == "active":
        if button_count != (red_button_cnt + green_button_cnt + yellow_button_cnt) OR (wave_timeout == True):
            pot_value = pot.read()
            Wavestate = "inactive"
            wavelength_timer.deinit()
            #Submit pot_val to server

def Wavelength_lobby():
    #Server decides who host/player are 
    #OPTIONAL: Potentiometer calibration
    #Based on server assignment call the appropriate host or player function
    if role == "host":
        Wavelength_host()
    elif role == "player":
        Wavelength_player()


###############MEMORY GAME#############


##########ROCK PAPER SCISSORS##########




##########MAIN LOOP##########

while True:
    #Server config
    #Send to game lobby for voting
    #based on vote, send to correct game function
    if game == "wavelength":
        Wavelength_lobby()
    elif game == "memory":
        Memory_lobby()
    elif game == "rock paper scissors":
        RPS_lobby()

