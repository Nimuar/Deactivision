# main.py central loop
import time
import machine
import minigames
import json
import memory

from machine import Pin
from minigames import lcd, scroll_message, show_message, btn, game_selection, WIFI_SSID, WIFI_PASS, SERVER_URL, DEVICE_NAME
from Server import ServerConn

# --- Central orchestrator ---
def main():
    
    #Checking/Installing Dependencies
    ServerConn.dependency_check()
    
    #Connect to wifi and server
    show_message(lcd, "Connecting to wifi :-)")
    ServerConn.connect_wifi(WIFI_SSID, WIFI_PASS)

    show_message(lcd, "Connecting to server...")
    websocket = ServerConn.connect_to_server(SERVER_URL)
    
    # init button state
    click_count, last_click_time, last_state = minigames.init_button_state()
    
    while True:
        current_time = time.ticks_ms()
        
        # Server?
        websocket = ServerConn.poll_server(websocket, handle_server_message)
            
        # Button Edge detection/game selection
        game, click_count, last_click_time, last_state = minigames.game_selection(btn, current_time, click_count, last_click_time, last_state)
        
        if game:
            websocket = ServerConn.send_game_selection(websocket, game, DEVICE_NAME)
        
def handle_server_message(msg, ws):
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