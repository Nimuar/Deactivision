from timeit import Timer

import machine
from machine import Pin
from machine import ADC
from machine import PWM
from machine import I2C
from lcd import LCD_I2C

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

##############I2C LCD SETUP##############
i2c = I2C(0, scl=Pin(22), sda=Pin(20), freq=400000)
# Scan for I2C devices
devices = i2c.scan()
print("I2C devices found:", devices)

lcd = LCD_I2C(i2c, address=0x27)

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

def beepSound(freq, duration):
    pwm_speaker.freq(freq)
    pwm_speaker.duty(512)
    sleep(duration)
    pwm_speaker.duty(0)

def lcd_print(text):
    """Print text to LCD"""
    lcd.print(text[:16])


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

    
def countdown_buzzer():
    # Rock
    lcd_print("Rock...")
    set_led("red")
    beepSound(600, 0.2)
    sleep(0.5)

    # Paper
    lcd_print("Paper...")
    set_led("green")
    beepSound(700, 0.2)
    sleep(0.5)

    # Scissors
    lcd_print("Scissors...")
    set_led("yellow")
    beepSound(800, 0.2)
    sleep(0.5)

    # Shoot!
    lcd_print("SHOOT!")
    clear_led()
    beepSound(1000, 0.3)


def get_player_selection():
    """Wait for player to press a button and return their choice"""
    global red_button_cnt, green_button_cnt, yellow_button_cnt
    
    # Reset button counters to start fresh
    red_button_cnt = 0
    green_button_cnt = 0
    yellow_button_cnt = 0
    
    # Display prompt on LCD
    lcd_print("Choose: R/G/Y")
    
    # Start timeout timer (5 seconds)
    start_time = time.time()
    timeout_seconds = 5
    
    # Wait for a button press or timeout
    while time.time() - start_time < timeout_seconds:
        if red_button_cnt > 0:
            return "rock"
        elif green_button_cnt > 0:
            return "paper"
        elif yellow_button_cnt > 0:
            return "scissors"
    
    # Timeout reached
    return "forfeit"


def send_selection_to_server(selection):
    """Placeholder function to send player selection to server"""
    # TODO: Implement actual server communication
    print(f"Sending {selection} to server")


def get_round_result():
    """Placeholder function to receive round result from server"""
    # TODO: Implement actual server communication
    # This would wait for server response
    return "win"  # Or "lose" or "tie" 


def RPS_lobby():
    """Rock Paper Scissors game lobby - handles role assignment"""
    # For now, assume player role (server would set this)
    if role == "host":
        RPS_host()  # Placeholder for host logic
    elif role == "player":
        RPS_player()
    elif role == "Spectator":
        RPS_spectator()

def RPS_spectator():
    """Spectator logic for Rock Paper Scissors"""
    # TODO: Implement spectator logic. Display "Waiting for your turn..." and then show results after player selection.
    pass


def RPS_player():
    """Player logic for Rock Paper Scissors"""
    # Start countdown
    countdown_buzzer()
    
    # Get player's selection
    selection = get_player_selection()
    
    # Send selection to server
    send_selection_to_server(selection)
    
    # Display selection confirmation
    if selection == "forfeit":
        lcd_print("Time's up! Forfeit")
    else:
        lcd_print(f"You chose: {selection}")
    sleep(2)  # Show for 2 seconds


def RPS_host():
    """Host logic for Rock Paper Scissors (placeholder)"""
    # TODO: Implement host logic. Not sure what we'd need here since the server is handling game logic
    pass


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

