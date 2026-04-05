# Standalone file for memory game (Simon-like game)
# Uses common functions from minigames.py 
# Can merge back into main later

# TODOs:
# - Implement server communication to get pattern
# - Play buzzer with button or success/failure?
# - Add scoring system?? - talk to server
# - Use real timers instead of sleep?? Not needed but prof might like more


import minigames as mg
from time import sleep, time
import random

# Game constants
PATTERN_LENGTH = 10
BLINK_DURATION = 0.3  # 300ms - how long each light blinks
BLINK_PAUSE = 0.2    # 200ms - pause between blinks
GAME_SPEED = 0.2     # Delay between sequence playback and user input phase

# Color mapping
COLORS = ["red", "green", "yellow"]
COLOR_TO_BUTTON = {
    "red": "red_button_cnt",
    "green": "green_button_cnt",
    "yellow": "yellow_button_cnt"
}

def play_pattern_sequence(pattern):
    """Play the light sequence from the pattern"""
    print("Playing pattern...")
    for color in pattern:
        mg.set_led(color)
        sleep(BLINK_DURATION)
        mg.clear_led()
        sleep(BLINK_PAUSE)
    sleep(GAME_SPEED)

def get_user_input(expected_pattern):
    """Wait for user to press buttons and validate against expected pattern"""
    print("Your turn! Press the buttons in order...")
    user_pattern = []
    prev_red_cnt = mg.red_button_cnt
    prev_green_cnt = mg.green_button_cnt
    prev_yellow_cnt = mg.yellow_button_cnt
    timeout_start = time()
    timeout = 10  # 10 second timeout per input
    
    while len(user_pattern) < len(expected_pattern):
        current_time = time()
        
        # Check for timeout
        if current_time - timeout_start > timeout:
            print("Timeout! No input received.")
            return None
        
        # Check if red button was pressed
        if mg.red_button_cnt > prev_red_cnt:
            pressed_color = "red"
            print("Red button pressed")
            user_pattern.append(pressed_color)
            mg.set_led("red")
            sleep(BLINK_DURATION)
            mg.clear_led()
            prev_red_cnt = mg.red_button_cnt
            
            # Validate immediately against expected pattern
            if user_pattern[-1] != expected_pattern[len(user_pattern) - 1]:
                print("Wrong button! Expected", expected_pattern[len(user_pattern) - 1])
                return None
            
            timeout_start = current_time  # Reset timeout on valid input
        
        # Check if green button was pressed
        elif mg.green_button_cnt > prev_green_cnt:
            pressed_color = "green"
            print("Green button pressed")
            user_pattern.append(pressed_color)
            mg.set_led("green")
            sleep(BLINK_DURATION)
            mg.clear_led()
            prev_green_cnt = mg.green_button_cnt
            
            # Validate immediately against expected pattern
            if user_pattern[-1] != expected_pattern[len(user_pattern) - 1]:
                print("Wrong button! Expected", expected_pattern[len(user_pattern) - 1])
                return None
            
            timeout_start = current_time  # Reset timeout on valid input
        
        # Check if yellow button was pressed
        elif mg.yellow_button_cnt > prev_yellow_cnt:
            pressed_color = "yellow"
            print("Yellow button pressed")
            user_pattern.append(pressed_color)
            mg.set_led("yellow")
            sleep(BLINK_DURATION)
            mg.clear_led()
            prev_yellow_cnt = mg.yellow_button_cnt
            
            # Validate immediately against expected pattern
            if user_pattern[-1] != expected_pattern[len(user_pattern) - 1]:
                print("Wrong button! Expected", expected_pattern[len(user_pattern) - 1])
                return None
            
            timeout_start = current_time  # Reset timeout on valid input
        
        sleep(0.01)  # Small delay to avoid busy waiting
    
    return user_pattern

def play_simon_game():
    """Main Simon game loop with progressive pattern reveal"""
    print("Starting Simon Light Game!")
    print("Generating pattern of", PATTERN_LENGTH, "lights...")
    
    # Generate random pattern
    pattern = [random.choice(COLORS) for _ in range(PATTERN_LENGTH)]            # TODO: Get the pattern from the server.
    print("Pattern generated!")
    print("Cheat sheet (for testing):", pattern)  # Remove or comment out in production
    
    # Progressive game - reveal one color at a time
    for level in range(1, PATTERN_LENGTH + 1):
        print("\n--- Level", level, "---")
        
        # Show the pattern up to current level
        revealed_pattern = pattern[:level]
        play_pattern_sequence(revealed_pattern)
        
        # Get user input for the revealed pattern
        user_input = get_user_input(revealed_pattern)
        
        # Check if user input is valid
        if user_input is None:
            print("Game Over - Wrong input!")
            # Flash red to indicate failure
            for _ in range(3):
                mg.set_led("red")
                sleep(0.2)
                mg.clear_led()
                sleep(0.2)
            return False
        
        print("Correct! Level", level, "complete!")
        sleep(0.5)    # Pause before next level
    
    # If we get here, user completed all levels
    print("\nSuccess! You completed all", PATTERN_LENGTH, "levels!")
    # Flash all LEDs to celebrate
    mg.set_led("all")
    sleep(0.5)
    mg.clear_led()
    sleep(0.5)
    return True

# Run the game
while True:
    result = play_simon_game()
    print("\nWant to play again? New game starts in 10...")
    sleep(10)