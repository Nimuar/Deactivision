import network
import time
import machine
import json
import gc
from neopixel import NeoPixel

# --- DEVICE CONFIGURATION ---
DEVICE_NAME = "ESP32_LEAD"
WIFI_SSID = "ssid"
WIFI_PASS = "pass"
SERVER_URL = f"ws://xxx.xxx.x.xxx:8000/ws/{DEVICE_NAME}" 

# --- Hardware Setup ---
PIN_NEO_PWR = 2
PIN_NEO_DATA = 0
neo_pwr = machine.Pin(PIN_NEO_PWR, machine.Pin.OUT)
neo_pwr.value(1)
np = NeoPixel(machine.Pin(PIN_NEO_DATA), 1)

uwebsockets = None

# btn = machine.Pin(38, machine.Pin.IN)

def set_led(color):
    np[0] = color
    np.write()

def connect_wifi():
    set_led((50, 0, 0)) 
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
            print(".", end="")
    print("\nWiFi Connected! IP:", wlan.ifconfig()[0])


# =========================================================
# DEPENDENCY CHECK & INSTALLATION
# =========================================================
def dependency_check():
    # 1. Connect to Wi-Fi FIRST so 'mip' has internet access
    connect_wifi()

    # 2. Check for third-party packages and install if missing
    print("\nChecking required packages...")
    try:
        import uwebsockets.client
        print("[+] 'uwebsockets' is already installed.")
    except ImportError:
        print("[!] 'uwebsockets' is MISSING. Installing via mip...")
        try:
            import mip
            
            print(" -> Installing 'logging'...")
            mip.install("logging")
            
            print(" -> Installing 'uwebsockets/client.py'...")
            mip.install("https://raw.githubusercontent.com/danni/uwebsockets/master/uwebsockets/client.py", target="/lib/uwebsockets")
            
            print(" -> Installing 'uwebsockets/protocol.py'...")
            mip.install("https://raw.githubusercontent.com/danni/uwebsockets/master/uwebsockets/protocol.py", target="/lib/uwebsockets")
            
            print("[+] Successfully installed dependencies.")
            import uwebsockets.client  # Import it now that it is installed
        except Exception as e:
            print(f"[X] Failed to install packages: {e}")
            set_led((50, 0, 0))
            while True: time.sleep(1)  # Halt execution if installation fails

#     # 3. Import local game modules AFTER dependencies are cleared
#     print("Importing local game modules...")
#     import memory
#     print("Local game modules have been imported")
# =========================================================


def connect_to_server():
    """Forces a connection loop until the server is reached."""
    while True:
        try:
            print(f"\nConnecting to Server: {SERVER_URL}")
            ws = uwebsockets.client.connect(SERVER_URL)
            ws.sock.setblocking(False)
            print("Server Connected!")
            set_led((0, 50, 0))
            return ws
        except Exception as e:
            print(f"Failed to connect: {e}. Retrying in 3 seconds...")
            set_led((50, 0, 0))
            time.sleep(3)

def server_loop(btn, lcd, show_message, handle_game_selection): #added by Mark to try to make this not run anything
    """
    Networking loop:
    - Handles button presses
    - Receives messages from server
    - Delegates game logic via handle_game_selection(msg, ws)
    """
    
    global uwebsockets
    dependency_check() 
    import uwebsockets.client
    
    websocket = connect_to_server()
    
    click_count = 0
    last_click_time = 0
    timeout_delay = 1000
    last_btn_state = 1  

    print("\nPRESS ONBOARD button once for memory game")
    show_message(lcd, "Press once for memory game")
    
    while True:
        try:
            time.sleep_ms(10)
            current_time = time.ticks_ms()
            
            # --- 1. NON-BLOCKING NETWORK READ ---
            try:
                incoming_data = websocket.recv()
                if incoming_data:
                    msg = json.loads(incoming_data)
                    handle_game_selection(msg, websocket)
                    
            except OSError:
                pass # No incoming data
                    
#                     if msg.get("type") == "PATTERN":
#                         patterns_array = msg.get("patterns")
#                         start_level = msg.get("start_level", 1) 
#                         print(f"\n[SERVER -> ESP32]: Downloaded {len(patterns_array)} levels starting at Level {start_level}.")
#                         
#                         print("\n[!] Disconnecting from server for offline gameplay...")
#                         set_led((0, 0, 50)) 
#                         try:
#                             websocket.close()
#                         except:
#                             pass
#                         
#                         results_log = memory.play_simon_game(patterns_array, start_level)
#                         
#                         print("\n[!] Game finished. Reconnecting to upload results...")
#                         websocket = connect_to_server()
#                         
#                         payload = {
#                             "type": "GAME_RESULTS",
#                             "device_id": DEVICE_NAME,
#                             "results": results_log
#                         }
#                         websocket.send(json.dumps(payload))
#                         print(f"--> Uploaded batch results: {results_log}")
#                         
#                         if "loss" not in results_log:
#                             print("\n[!] Perfect score! Waiting for the next batch of levels from the server...")
#                         else:
#                             print("\n[!] Game Over. Listening for new game selection...")
# 
#             except OSError:
#                 pass 
            
            # --- 2. BUTTON EDGE DETECTION ---
            current_btn_state = btn.value()
            if current_btn_state == 0 and last_btn_state == 1:
                if time.ticks_diff(current_time, last_click_time) > 50:
                    click_count += 1
                    last_click_time = current_time
                    print(f"Click! (Count: {click_count})")
            last_btn_state = current_btn_state
             
            # --- 3. PROCESS GAME SELECTION ---
            if click_count > 0 and time.ticks_diff(current_time, last_click_time) > timeout_delay:
                handle_game_selection({"type": "BUTTON", "clicks": click_count}, websocket)
                click_count = 0
                gc.collect()
                
                game_selection = ""
                
                if click_count == 1:
                    game_selection = "led_memory"
                    print("\n[!] Selected: LED Memory Game")
                elif click_count == 2:
                    game_selection = "rps"
                    print("\n[!] Selected: Rock Paper Scissors")
                elif click_count == 3:
                    game_selection = "wavelength"
                    print("\n[!] Selected: Wavelength")
                else:
                    print(f"\n[X] Invalid input: {click_count} clicks. Resetting.")
                    game_selection = None
                 
#               if game_selection:
#                   payload = {
#                       "type": "GAME_SELECT",
#                       "device_id": DEVICE_NAME,
#                       "game": game_selection
#                   }
#                   try:
#                       websocket.send(json.dumps(payload))
#                       print("--> Sent request to server.")
#                      except OSError:
#                       print("\n[!] Connection lost during send. Reconnecting...")
#                       websocket = connect_to_server()
#                       websocket.send(json.dumps(payload))
#                 
#              click_count = 0
#              gc.collect()

        except Exception as master_e:
            print(f"\n[!] Network connection dropped: {master_e}. Reconnecting...")
            websocket = connect_to_server()

# if __name__ == "__main__":
#     set_led((50, 0, 0))
#     main()

