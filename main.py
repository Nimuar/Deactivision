# main.py central loop
import time
import machine
import minigames
import json
import memory

from machine import Pin
from minigames import lcd, scroll_message, show_message, btn
from Server import ServerConn


# --- Central orchestrator ---
def main():
    show_message(lcd, "Welcome to Minigames :-)")
    #import memory

    # Initialize server connection
    print("Connecting to server...")

    # Run server loop
    ServerConn.server_loop(btn,
                           lcd,
                           show_message,
                           handle_game_selection=handle_game_selection)
    
#     print("\nPRESS ONBOARD button once for memory game")
#     show_message(lcd, "Press once for memory game")
    
    # Main loop: handle button input and server messages
    while True:
        # Example: scroll welcome message while waiting for input
        scroll_message(lcd, "Press button to select game...", row=0, speed=0.2, duration=2)

        # --- 3a. Check for server messages ---
        try:
            msg = websocket.recv()  # non-blocking read inside try/except
            if msg:
                ServerConn.handle_message(msg)  # define a handler in ServerConn
        except:
            pass

        # --- 3b. Check button press ---
        if btn.value() == 1:
            print("Button pressed!")
            # Decide which game to start based on clicks or other logic
            # e.g., memory_game(), rps(), wavelength() from minigames.py

        # --- 3c. Small delay to avoid CPU hogging ---
        time.sleep_ms(10)
        
def handle_game_selection(msg, ws):
    """Callback for ServerConn: handle incoming messages or button clicks."""
    if msg["type"] == "PATTERN":
        # Offline memory game triggered by server
        patterns_array = msg.get("patterns")
        start_level = msg.get("start_level", 1)
        print(f"[SERVER -> ESP32] Downloaded {len(patterns_array)} levels")
        results_log = memory.play_simon_game(patterns_array, start_level)
        ws.send(json.dumps({
            "type": "GAME_RESULTS",
            "device_id": minigames.DEVICE_NAME,
            "results": results_log
        }))
        print(f"[RESULTS] Uploaded batch results: {results_log}")

    elif msg["type"] == "BUTTON":
        # User clicked onboard button
        clicks = msg["clicks"]
        game_map = {1: "led_memory", 2: "rps", 3: "wavelength"}
        game_selection = game_map.get(clicks)
        if game_selection:
            print(f"[GAME] Selected: {game_selection}")
            ws.send(json.dumps({
                "type": "GAME_SELECT",
                "device_id": minigames.DEVICE_NAME,
                "game": game_selection
            }))

if __name__ == "__main__":
    main()