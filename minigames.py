import machine
from machine import Pin, ADC, PWM, Timer

##############GPIO SETUP##############
led_board = Pin(13, Pin.OUT)
red_led = Pin(12, Pin.OUT)
green_led = Pin(27, Pin.OUT)
yellow_led = Pin(33, Pin.OUT)

red_button = Pin(19, Pin.IN, Pin.PULL_UP)
green_button = Pin(5, Pin.IN, Pin.PULL_UP)
yellow_button = Pin(4, Pin.IN, Pin.PULL_UP)
red_button_pressed = False
green_button_pressed = False
yellow_button_pressed = False
_red_debounce_active = False
_green_debounce_active = False
_yellow_debounce_active = False
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
    elif color == "all":
        red_led.value(1)
        green_led.value(1)
        yellow_led.value(1)

def clear_led():
        red_led.value(0)
        green_led.value(0)
        yellow_led.value(0)


###########INTERRUPTS################   
    
def yellow_buttonpress(pin):
    global _yellow_debounce_active
    if not _yellow_debounce_active:
        _yellow_debounce_active = True
        button_timer.init(period=20, mode=Timer.ONE_SHOT, callback=debounce_yellow)

def green_buttonpress(pin):
    global _green_debounce_active
    if not _green_debounce_active:
        _green_debounce_active = True
        button_timer.init(period=20, mode=Timer.ONE_SHOT, callback=debounce_green)
    
def red_buttonpress(pin):
    global _red_debounce_active
    if not _red_debounce_active:
        _red_debounce_active = True
        button_timer.init(period=20, mode=Timer.ONE_SHOT, callback=debounce_red)

def debounce_yellow(t):
    global yellow_button_pressed, _yellow_debounce_active, yellow_button_cnt
    if yellow_button.value() == 1:
        yellow_button_pressed = True
        yellow_button_cnt = yellow_button_cnt + 1
    _yellow_debounce_active = False

def debounce_green(t):
    global green_button_pressed, _green_debounce_active, green_button_cnt
    if green_button.value() == 1:
        green_button_pressed = True
        green_button_cnt = green_button_cnt + 1
    _green_debounce_active = False

def debounce_red(t):
    global red_button_pressed, _red_debounce_active, red_button_cnt
    if red_button.value() == 1:
        red_button_pressed = True
        red_button_cnt = red_button_cnt + 1
    _red_debounce_active = False


red_button.irq(handler=red_buttonpress, trigger=Pin.IRQ_RISING)
green_button.irq(handler=green_buttonpress, trigger=Pin.IRQ_RISING)
yellow_button.irq(handler=yellow_buttonpress, trigger=Pin.IRQ_RISING)

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
    wavelength_timer.init(period=30000, mode=Timer.ONE_SHOT, callback=wavelength_timeout)   #Start 30sec timer
    #Display countdown on board?
    #Read POT if we need to display it, otherwise just read when timer expires or button is hit. 
    pot_timer.init(period=100, mode=Timer.PERIODIC, callback=potread)
    #Display POT(0-100%) on board as feedback?
    #IF any button is pressed, or if 30sec timer expires then save and submit POT
    while Wavestate == "active":
        if button_count != (red_button_cnt + green_button_cnt + yellow_button_cnt) or (wave_timeout == True):
            pot_value = pot.read()
            score = (4096 - pot_value) / 4096 * 100
            Wavestate = "inactive"
            wavelength_timer.deinit()
            #Submit score to server -  need help Henry/Tom
    #do we want to wait for server to send back the winner before returning to lobby?
    return

def Wavelength_host():
    global red_button_pressed, yellow_button_pressed, green_button_pressed
    red_button_pressed = False
    green_button_pressed = False
    yellow_button_pressed = False
    #Host receives 3 word & category and displays to player - need help Henry/Tom
    Wavestate = "active"
    while Wavestate == "active":
        if red_button_pressed:
            waveword = "red" #placeholder for actual word received from server corresponding to red button
            pot_value = pot.read()
            score = (4096 - pot_value) / 4096 * 100
            #send score to server - need help Henry/Tom
            Wavestate = "inactive"
        elif green_button_pressed:
            waveword = "green" #placeholder for actual word received from server corresponding to green button
            pot_value = pot.read()
            score = (4096 - pot_value) / 4096 * 100
            #send score to server - need help Henry/Tom
            Wavestate = "inactive"
        elif yellow_button_pressed:
            waveword = "yellow" #placeholder for actual word received from server corresponding to yellow button
            pot_value = pot.read()
            score = (4096 - pot_value) / 4096 * 100
            #send score to server - need help Henry/Tom
            Wavestate = "inactive"        
    return

def Wavelength_lobby():
    #Server decides who host/player are - need help Henry/Tom getting the role from server
    #OPTIONAL: Potentiometer calibration
    #Based on server assignment call the appropriate host or player function
    if role == "host":
        Wavelength_host()
    elif role == "player":
        Wavelength_player()
    return
    #decide when to return to main function - maybe after each round or after a set number of rounds?

###############MEMORY GAME#############


##########ROCK PAPER SCISSORS##########




##########MAIN LOOP##########

'''
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
'''
