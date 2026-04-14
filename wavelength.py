import machine
import time

# --- Hardware Setup ---
# Potentiometer on GPIO34
pot = machine.ADC(machine.Pin(34))
pot.atten(machine.ADC.ATTN_11DB)   
pot.width(machine.ADC.WIDTH_12BIT) 

# Colored action buttons 
btn_red = machine.Pin(19, machine.Pin.IN, machine.Pin.PULL_DOWN)
btn_green = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_DOWN)
btn_yellow = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_DOWN)

# Speaker Setup (GPIO 32)
speaker = machine.PWM(machine.Pin(32))
speaker.duty_u16(0) # Start silent!

# --- Audio Functions ---
def play_tone(freq, duration_ms):
    """Plays a brief tone on the speaker."""
    if freq > 0:
        speaker.freq(freq)
        speaker.duty_u16(32768) # 50% volume
    else:
        speaker.duty_u16(0)
    time.sleep_ms(duration_ms)
    speaker.duty_u16(0) # Always mute after playing

def sound_click():
    """Short blip for button presses."""
    play_tone(800, 30)

def sound_lock_in():
    """Happy 3-note chime when locking in a score."""
    play_tone(523, 100) # C5
    time.sleep_ms(30)
    play_tone(659, 100) # E5
    time.sleep_ms(30)
    play_tone(784, 200) # G5

# --- Game Logic ---
def wait_for_lock_in():
    print("\n<<< Turn the dial to your target >>>")
    print("<<< Press RED, GREEN, or YELLOW to lock it in! >>>\n")
    
    last_printed_score = -1
    
    while True:
        raw_val = pot.read()
        score = int((raw_val / 4095.0) * 100)
        
        if score != last_printed_score:
            print(f"Current Dial: [ {score}% ]    ", end="\r")
            last_printed_score = score
        
        if btn_red.value() == 1 or btn_green.value() == 1 or btn_yellow.value() == 1:
            while btn_red.value() == 1 or btn_green.value() == 1 or btn_yellow.value() == 1:
                time.sleep_ms(10)
                
            sound_lock_in() # Play the success chime!
            print(f"\n\n+++ LOCKED IN AT {score}% +++")
            return score
            
        time.sleep_ms(50)

def host_offline_phase(words_list, onboard_btn):
    print("\n========================================")
    print(" +++ YOU ARE THE HOST +++")
    print("========================================")
    print("Select a category by clicking the onboard button 1 to 5 times:\n")
    for w in words_list:
        print(f"  {w}")
    print("\nWaiting for your selection (Pause clicking to confirm)...")

    click_count = 0
    last_click_time = time.ticks_ms()
    last_btn_state = onboard_btn.value()
    
    while True:
        current_time = time.ticks_ms()
        current_btn_state = onboard_btn.value()
        
        if current_btn_state == 0 and last_btn_state == 1:
            if time.ticks_diff(current_time, last_click_time) > 50:
                sound_click() # Play a tick sound per click
                click_count += 1
                last_click_time = current_time
                print(f"  Click {click_count}...")
        
        last_btn_state = current_btn_state
        
        if click_count > 0 and time.ticks_diff(current_time, last_click_time) > 2000:
            if click_count > 5: 
                click_count = 5 
            play_tone(440, 200) # Confirmation tone
            print(f"\n+++ You selected Option {click_count}! +++")
            break
            
        time.sleep_ms(10)
        
    score = wait_for_lock_in()
    return click_count, score

def player_offline_phase(word):
    print("\n========================================")
    print(" +++ YOU ARE A GUESSER +++")
    print("========================================")
    print(f"The Host's Category is:\n\n   <<< {word} >>>\n")
    
    # Alert the guesser it's their turn
    play_tone(600, 150) 
    time.sleep_ms(100)
    play_tone(600, 150)
    
    score = wait_for_lock_in()
    return score