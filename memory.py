import minigames as mg
import time

# --- GAME CONSTANTS ---
BLINK_DURATION = 0.5 
BLINK_PAUSE = 0.5     
GAME_SPEED = 0.5    
TIMEOUT_MS = 15000    

def play_pattern_sequence(pattern):
    print("\nEyes on the board!")

    print(f"Sequence starting...")
    mg.lcd_print("Eyes on the LEDs!")
    time.sleep(3)
        
    print("Playing pattern...")
    print(f"Cheat sheet (for testing): {pattern}")
    
    for color in pattern:
        mg.set_led(color)
        time.sleep(BLINK_DURATION)
        mg.clear_led()
        time.sleep(BLINK_PAUSE)
        
    time.sleep(GAME_SPEED)

def get_user_input(expected_pattern):
    print(f"\n>>> Your turn! Press the buttons in order... (You have {TIMEOUT_MS//1000} seconds) <<<")
    mg.lcd_print("Press buttons in order! ")
    user_pattern = []
    
    prev_red_cnt = mg.red_button_cnt
    prev_green_cnt = mg.green_button_cnt
    prev_yellow_cnt = mg.yellow_button_cnt
    
    timeout_start = time.ticks_ms()
    
    while len(user_pattern) < len(expected_pattern):
        current_time = time.ticks_ms()
        
        if time.ticks_diff(current_time, timeout_start) > TIMEOUT_MS:
            print("Timeout! No input received.")
            mg.lcd_print("Timeout! No input received.")
            return None
        
        pressed_color = None
        
        if mg.red_button_cnt > prev_red_cnt:
            pressed_color = "red"
            prev_red_cnt = mg.red_button_cnt
        elif mg.green_button_cnt > prev_green_cnt:
            pressed_color = "green"
            prev_green_cnt = mg.green_button_cnt
        elif mg.yellow_button_cnt > prev_yellow_cnt:
            pressed_color = "yellow"
            prev_yellow_cnt = mg.yellow_button_cnt

        if pressed_color:
            print(f"{pressed_color.upper()} button pressed!")
            #mg.lcd_print(f"{pressed_color.upper()} button pressed!")
            user_pattern.append(pressed_color)
            
            mg.set_led(pressed_color)
            time.sleep(0.4) 
            mg.clear_led()
            
            if user_pattern[-1] != expected_pattern[len(user_pattern) - 1]:
                print(f"Wrong button! Expected {expected_pattern[len(user_pattern) - 1].upper()}")
                mg.lcd_print(f"Wrong button! Expected {expected_pattern[len(user_pattern) - 1].upper()}")
                return None
            
            timeout_start = time.ticks_ms()
        
        time.sleep(0.01)  
    
    return user_pattern


def play_simon_game(server_patterns_array, start_level=1):
    """
    Takes an array of arrays representing the patterns, and the starting level number.
    Returns the score as an integer representing the number of levels beaten.
    Score starts at (start_level - 1) to account for previously completed levels.
    """
    print(f"\n=== Starting Offline-Batched Simon Game (Levels {start_level} - {start_level + len(server_patterns_array) - 1}) ===")
    score = start_level - 1  # Score reflects total levels completed, not just this batch
    
    for idx, level_pattern in enumerate(server_patterns_array):
        # Calculate the actual continuous level number
        level = start_level + idx 
        print(f"\n--- Level {level} ---")
        
        play_pattern_sequence(level_pattern)
        
        user_input = get_user_input(level_pattern)
        
        if user_input is None:
            print("\nGame Over - Wrong input or Timeout!")
            mg.lcd_print("Game Over!")
            for _ in range(3):
                mg.set_led("red")
                time.sleep(0.5)
                mg.clear_led()
                time.sleep(0.5)
            return score
            
        print(f"Correct! Level {level} complete!")
        mg.lcd_print(f"Correct! Level {level} complete!")
        score += 1
        time.sleep(1.0)
    
    print(f"\nSuccess! You completed up to Level {start_level + len(server_patterns_array) - 1}!")
    mg.lcd_print(f"\nSuccess! You completed up to Level {start_level + len(server_patterns_array) - 1}!")
    mg.set_led("all")
    time.sleep(2.0)
    mg.clear_led()
    return score