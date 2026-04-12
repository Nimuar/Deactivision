import minigames as mg
from time import sleep
import time
import json

##########ROCK PAPER SCISSORS##########

def countdown_buzzer():
    # Rock
    mg.lcd_print("Rock...")
    mg.set_led("red")
    mg.beepSound(600, 0.2)
    sleep(0.5)
    mg.clear_led()

    # Paper
    mg.lcd_print("Paper...")
    mg.set_led("green")
    mg.beepSound(700, 0.2)
    sleep(0.5)
    mg.clear_led()

    # Scissors
    mg.lcd_print("Scissors...")
    mg.set_led("yellow")
    mg.beepSound(800, 0.2)
    sleep(0.5)
    mg.clear_led()

    # Shoot!
    mg.lcd_print("SHOOT!")
    mg.clear_led()
    mg.beepSound(1000, 0.3)
    sleep(0.2)
    mg.clear_led()

def get_player_selection():
    """Wait for player to press a button and return their choice (with 5-second timeout)"""
    mg.red_button_cnt = 0
    mg.green_button_cnt = 0
    mg.yellow_button_cnt = 0

    start_time = time.time()
    timeout_seconds = 5

    while time.time() - start_time < timeout_seconds:
        if mg.red_button_cnt > 0:
            mg.lcd_print("Rock!")
            mg.set_led("red")
            mg.beepSound(600, 0.2)
            return "rock"
        elif mg.green_button_cnt > 0:
            mg.lcd_print("Paper!")
            mg.set_led("green")
            mg.beepSound(700, 0.2)
            return "paper"
        elif mg.yellow_button_cnt > 0:
            mg.lcd_print("Scissors!")
            mg.set_led("yellow")
            mg.beepSound(800, 0.2)
            return "scissors"

    mg.lcd_print("Forfeit!")
    return "forfeit"

def send_selection_to_server(selection, websocket, device_id):
    """Send player selection to server via WebSocket"""
    try:
        payload = {
            "type": "RPS_SELECTION",
            "device_id": device_id,
            "selection": selection
        }
        websocket.send(json.dumps(payload))
        print(f"Sent selection to server: {selection}")
        return True
    except Exception as e:
        print(f"Failed to send selection: {e}")
        return False

def get_round_result(websocket):
    """Wait for and receive round result from server"""
    try:
        # Wait for server response with timeout
        timeout_ms = 5000  # 5 second timeout
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            try:
                incoming_data = websocket.recv()
                if incoming_data:
                    msg = json.loads(incoming_data)
                    if msg.get("type") == "RPS_RESULT":
                        result = msg.get("result")
                        print(f"Received result from server: {result}")
                        return result
            except OSError:
                # No data available, continue waiting
                pass
            time.sleep_ms(10)  # Small delay to prevent busy waiting
        
        print("Timeout waiting for server result")
        return "timeout"
        
    except Exception as e:
        print(f"Failed to receive result: {e}")
        return "error"

def RPS_lobby(websocket=None):
    """Rock Paper Scissors game lobby - handles role assignment"""
    # Server decides who host/player are
    # Based on server assignment call the appropriate host or player function
    if mg.role == "host":
        RPS_host(websocket)
    elif mg.role == "player":
        RPS_player(websocket)
    elif mg.role == "Spectator":
        RPS_spectator(websocket)

def RPS_spectator(websocket=None):
    """Spectator logic for Rock Paper Scissors"""
    # TODO: Implement spectator logic. Display "Waiting for your turn..." and then show results after player selection.
    mg.lcd_print("Spectator Mode")
    pass

def RPS_player(websocket=None, device_id=None):
    """Player logic for Rock Paper Scissors tournament"""
    while True:  # Tournament loop - continue until eliminated
        countdown_buzzer()

        selection = get_player_selection()

        if websocket:
            success = send_selection_to_server(selection, websocket, device_id)
            if not success:
                mg.lcd_print("Connection Error")
                break
        else:
            print(f"Would send {selection} to server (no websocket)")

        if selection == "forfeit":
            mg.lcd_print("Forfeited! Eliminated")
            sleep(2)
            break

        mg.lcd_print(f"You chose: {selection}")
        sleep(1)

        if websocket:
            result = get_round_result(websocket)
        else:
            result = "win"

        if result == "win":
            mg.lcd_print("Round won! Next round...")
            sleep(2)
        elif result == "lose":
            mg.lcd_print("Round lost! Eliminated")
            sleep(2)
            break
        elif result == "tie":
            mg.lcd_print("It's a tie! Replay")
            sleep(2)
        elif result == "timeout" or result == "error":
            mg.lcd_print("Server Error")
            sleep(2)
            break

def RPS_host(websocket=None):
    """Host logic for Rock Paper Scissors (placeholder)"""
    # TODO: Implement host logic. Not sure what we'd need here since the server is handling game logic
    mg.lcd_print("Host Mode")
    pass

##########MAIN LOOP##########

if __name__ == "__main__":
    countdown_buzzer()
    get_player_selection()



