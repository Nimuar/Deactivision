import machine, time
from machine import Pin
from machine import ADC
from machine import PWM
from machine import Timer
from machine import I2C
from Server import ServerConn

from lcd_i2c.lcd_i2c import LCD
from neopixel import NeoPixel

##############LCD DEMO TEXT###############
#sda = Pin(22)
#scl = Pin(21) #Pin(20) does not exist for some reason

# ---------- Demo Text ----------
# print("Printing Hello World on LCD")
# 
# lcd.print("Hello World!")
# time.sleep(2)
# 
# lcd.clear()
# lcd.print("ESP32 LCD Test")
# time.sleep(2)

# ---------- Example Scrolling ----------
# for i in range(16):
#     lcd.clear()
#     lcd.print("Scroll Example")
#     lcd.set_cursor(i, 1)  # move second line
#     lcd.print(">>>")
#     time.sleep(0.3)

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

btn = Pin(38, Pin.IN, Pin.PULL_UP)

button_timer = Timer(0)
pot_timer = Timer(1)
wavelength_timer = Timer(2)
wave_timeout = False

pot = ADC(Pin(34, Pin.IN))
pwm_speaker = PWM(Pin(32), freq=10, duty_u16=512)

PIN_NEO_PWR = 2
PIN_NEO_DATA = 0
neo_pwr = machine.Pin(PIN_NEO_PWR, machine.Pin.OUT)
neo_pwr.value(1)
np = NeoPixel(machine.Pin(PIN_NEO_DATA), 1)

# LCD
i2c = I2C(0, scl=Pin(21), sda=Pin(22), freq=400_000)
devices = i2c.scan()
if devices:
    print("I2C devices found:", [hex(dev) for dev in devices])
else:
    print("No I2C devices found. Check wiring and power!")
lcd = LCD(addr=0x27, cols=16, rows=2, i2c=i2c)
lcd.begin()

game = "none"
role = "none"

##########COMMON FUNCTIONS##########

def set_neo_color(color):
    np[0] = color
    np.write()

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


def clear_lcd(lcd):
    """Clear the LCD display."""
    lcd.clear()

def print_line(lcd, text, row=0):
    """
    Print text to a specific row.
    If text is longer than lcd.cols, it scrolls automatically.
    """
    text = str(text)
    cols = lcd.cols  # number of columns on your lcd
    lcd.set_cursor(0, row)
    
    if len(text) <= cols:
        lcd.print(text)
    else:
        # Scroll text
        for i in range(len(text) - cols + 1):
            lcd.set_cursor(0, row)
            lcd.print(text[i:i+cols])
            time.sleep(0.3)

def show_message(lcd, message):
    """
    Display a message across multiple lines.
    Automatically wraps text to next line if needed.
    """
    rows = lcd.rows
    cols = lcd.cols
    lines = []

    # split message into lines
    while message:
        lines.append(message[:cols])
        message = message[cols:]

    lcd.clear()
    for i, line in enumerate(lines[:rows]):
        lcd.set_cursor(0, i)
        lcd.print(line)
        
def scroll_message(lcd, text, row=0, speed=0.2, duration=100):
    """
    Scrolls a message continuously across one row of the LCD.
    
    :param lcd: the LCD instance
    :param text: the text to scroll
    :param row: row index (0 or 1)
    :param speed: delay between scroll steps
    """
    display_width = lcd.cols
    text = str(text)
    
    # pad text with spaces equal to display width for smooth wrap-around
    scroll_text = text + " " * display_width

    start = time.ticks_ms()

    print("scroll on LCD")
    while time.ticks_diff(time.ticks_ms(), start) < duration * 1000:
        for i in range(len(scroll_text) - display_width + 1):
            lcd.set_cursor(0, row)
            lcd.print(scroll_text[i:i+display_width])
            time.sleep(speed)

            # early exit if button pressed to select game
            if btn.value() is 0:
                clear_lcd(lcd)
                return
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
    
def debounce_btn(t):
    global btn_cnt
    btn_cnt = btn_cnt + 1


red_button.irq(handler=red_buttonpress,trigger=Pin.IRQ_RISING)
#red_button.irq(handler=red_buttonpress,trigger=Pin.IRQ_FALLING)
green_button.irq(handler=green_buttonpress,trigger=Pin.IRQ_RISING)
yellow_button.irq(handler=yellow_buttonpress,trigger=Pin.IRQ_RISING)

##########SERVER CONFIGURATION#########
DEVICE_NAME = "ESP32_LEAD"
WIFI_SSID = ""
WIFI_PASS = ""
SERVER_URL = f"ws://xxx.xxx.x.xxx:8000/ws/{DEVICE_NAME}" 


############GAME SELECTIOIN###########
# --- BUTTON GAME SELECTION STATE ---
click_count = 0
last_state = 1
last_click_time = 0
timeout_delay = 1000


def init_button_state():
    global click_count, last_state, last_click_time
    click_count = 0
    last_state = 1
    last_click_time = 0
    print("Press onboard button to select game")
    show_message(lcd, "Press onboard button to select game")
    return click_count, last_click_time, last_state


def game_selection(btn, current_time, click_count, last_click_time, last_state):
    current_button_state = btn.value()
    #print("button.value():", current_button_state)

    # --- edge detection (falling edge: pressed) ---
    if current_button_state == 1 and last_state == 0:
        if time.ticks_diff(current_time, last_click_time) > 50:
            click_count += 1
            last_click_time = current_time
            print(f"Click! (Count: {click_count})")

    last_state = current_button_state

    game_selected = None

    # --- timeout selection ---
    if click_count > 0 and time.ticks_diff(current_time, last_click_time) > timeout_delay:
        if click_count == 1:
            game_selected = "led_memory"
        elif click_count == 2:
            game_selected = "rps"
        elif click_count == 3:
            game_selected = "wavelength"
        else:
            print(f"[X] Invalid input: {click_count} clicks.")

        click_count = 0

    return game_selected, click_count, last_click_time, last_state
###############WAVELENGTH##############
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
        if button_count != (red_button_cnt + green_button_cnt + yellow_button_cnt) or (wave_timeout == True):
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

    
#     #Server config
#     #Send to game lobby for voting
#     #based on vote, send to correct game function
#     if game == "wavelength":
#         Wavelength_lobby()
#     elif game == "memory":
#         Memory_lobby()
#     elif game == "rock paper scissors":
#         RPS_lobby()
#     else:
#         print("No game selected")

