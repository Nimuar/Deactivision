import network
import time
import machine
import json
import gc
import ubinascii 
from neopixel import NeoPixel

# --- DEVICE CONFIGURATION (DYNAMIC PLUG-AND-PLAY) ---
# Generate a unique ID using the last 4 characters of the ESP32's hardware MAC address
mac_bytes = machine.unique_id()
mac_str = ubinascii.hexlify(mac_bytes).decode('utf-8').upper()
short_id = mac_str[-4:] 

DEVICE_NAME = f"PLAYER_{short_id}"

WIFI_SSID = "ATTXvnW88k"
WIFI_PASS = "t846j?v2jrvk"
SERVER_IP = "192.168.1.69" 
SERVER_URL = f"wss://minigames-render.onrender.com/ws/{DEVICE_NAME}"

print("====================================")
print(f" +++ THIS BOARD IS: {DEVICE_NAME} +++")
print("====================================") 

# --- Hardware Setup ---
PIN_NEO_PWR = 2
PIN_NEO_DATA = 0
neo_pwr = machine.Pin(PIN_NEO_PWR, machine.Pin.OUT)
neo_pwr.value(1)
np = NeoPixel(machine.Pin(PIN_NEO_DATA), 1)

btn = machine.Pin(38, machine.Pin.IN)

# Mute the speaker immediately at boot
speaker = machine.PWM(machine.Pin(32))
speaker.duty_u16(0) 

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
connect_wifi()

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
        import uwebsockets.client  
    except Exception as e:
        print(f"[X] Failed to install packages: {e}")
        set_led((50, 0, 0))
        while True: time.sleep(1)

# Import local game modules AFTER dependencies are cleared
import memory 
import wavelength 
import rockpaperscissor
# =========================================================

def connect_to_server():
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

def main():
    websocket = connect_to_server()
    
    click_count = 0
    last_click_time = 0
    timeout_delay = 1000
    last_btn_state = 1  

    # Play a happy boot-up sequence
    wavelength.play_tone(440, 100)
    wavelength.play_tone(659, 150)

    print("\n=== LOBBY READY ===")
    print("PRESS ONBOARD button:")
    print(" 1x -> Memory Game")
    print(" 2x -> Rock Paper Scissors")
    print(" 3x -> Wavelength")
    
    while True:
        try:
            time.sleep_ms(10)
            current_time = time.ticks_ms()
            
            # --- 1. NON-BLOCKING NETWORK READ ---
            try:
                incoming_data = websocket.recv()
                if incoming_data:
                    msg = json.loads(incoming_data)
                    msg_type = msg.get("type")
                    
                    if msg_type == "PATTERN":
                        patterns_array = msg.get("patterns")
                        start_level = msg.get("start_level", 1) 
                        print(f"\n[SERVER -> ESP32]: Downloaded {len(patterns_array)} levels starting at Level {start_level}.")
                        
                        print("\n[!] Disconnecting from server for offline gameplay...")
                        set_led((0, 0, 50)) 
                        try: websocket.close()
                        except: pass
                        
                        score = memory.play_simon_game(patterns_array, start_level)
                        
                        print("\n[!] Game finished. Reconnecting to upload results...")
                        websocket = connect_to_server()
                        
                        payload = {
                            "type": "GAME_RESULTS",
                            "device_id": DEVICE_NAME,
                            "score": score
                        }
                        websocket.send(json.dumps(payload))
                        print(f"--> Uploaded score: {score}")
                        
                        if score == len(patterns_array):
                            print("\n[!] Perfect score! Waiting for next batch...")
                        else:
                            print("\n[!] Game Over. Listening for new game selection...")
                    
                    elif msg_type == "MEMORY_RESULTS":
                        # Memory game batch results (multiplayer)
                        winner = msg.get("winner")
                        winner_score = msg.get("winner_score")
                        all_scores = msg.get("all_scores")
                        
                        print("\n==========================")
                        print(" +++ MEMORY GAME COMPLETE +++")
                        print("==========================")
                        print(f"Winner: {winner}")
                        print(f"Winner Score: {winner_score}")
                        print("All Scores:")
                        for player, score in all_scores.items():
                            marker = " (YOU)" if player == DEVICE_NAME else ""
                            print(f"  {player}: {score}{marker}")
                        print("==========================\n")
                        print("LOBBY READY: Click onboard to start next game.")
                        print("PRESS ONBOARD button:")
                        print(" 1x -> Memory Game")
                        print(" 2x -> Rock Paper Scissors")
                        print(" 3x -> Wavelength")
                        set_led((0, 50, 0))
                    elif msg.get("type") == "RPS_READY":
                        print(f"\n[SERVER -> ESP32]: {msg.get('message', 'RPS ready')} (game id: {msg.get('game_id')})")
                        rockpaperscissor.RPS_player(websocket, DEVICE_NAME)
                        print("\n[!] RPS session ended. Listening for new game selection...")

                    elif msg_type == "WAVELENGTH_ROLE":
                        role = msg.get("role")
                        
                        if role == "host":
                            words_list = msg.get("words")
                            set_led((50, 0, 50)) # Purple for Host
                            
                            try: websocket.close() 
                            except: pass 
                            
                            word_idx, target_score = wavelength.host_offline_phase(words_list, btn)
                            
                            websocket = connect_to_server()
                            websocket.send(json.dumps({
                                "type": "HOST_SUBMIT",
                                "device_id": DEVICE_NAME,
                                "word_index": word_idx,
                                "score": target_score
                            }))
                            print("\n[+] Host data submitted! Watch the guessers lock in.")
                            
                        elif role == "player_wait":
                            set_led((0, 0, 50)) # Blue for Waiting
                            print("\n<<< Waiting for HOST to select word and value... >>>")
                            
                            try: websocket.close() 
                            except: pass 
                            
                            time.sleep(3) 
                            
                            websocket = connect_to_server()
                            websocket.send(json.dumps({
                                "type": "GAME_SELECT",
                                "device_id": DEVICE_NAME,
                                "game": "wavelength"
                            }))
                            
                        elif role == "player_guess":
                            word_to_guess = msg.get("word")
                            set_led((50, 50, 0)) # Yellow for Guesser
                            
                            try: websocket.close() 
                            except: pass 
                            
                            guess_score = wavelength.player_offline_phase(word_to_guess)
                            
                            websocket = connect_to_server()
                            websocket.send(json.dumps({
                                "type": "PLAYER_GUESS",
                                "device_id": DEVICE_NAME,
                                "score": guess_score
                            }))
                            print("\n[+] Guess submitted! Waiting for round results...")

                    elif msg_type == "ROUND_RESULTS":
                        # Play a big fanfare when results arrive
                        wavelength.sound_lock_in()
                        
                        print("\n==========================")
                        print(" +++ ROUND COMPLETE +++")
                        print("==========================")
                        print(f"Target Score: {msg.get('target')}%")
                        print("Guesses:")
                        for device, score in msg.get('guesses').items():
                            print(f"  {device}: {score}%")
                        print("==========================\n")
                        print("LOBBY READY: Click onboard to start next round.")
                        print("PRESS ONBOARD button:")
                        print(" 1x -> Memory Game")
                        print(" 2x -> Rock Paper Scissors")
                        print(" 3x -> Wavelength")
                        set_led((0, 50, 0))

            except OSError:
                pass 
            
            # --- 2. BUTTON EDGE DETECTION ---
            current_btn_state = btn.value()
            if current_btn_state == 0 and last_btn_state == 1:
                if time.ticks_diff(current_time, last_click_time) > 50:
                    click_count += 1
                    last_click_time = current_time
                    wavelength.sound_click() # Speaker click feedback in Lobby!
                    print(f"Click! (Count: {click_count})")
            last_btn_state = current_btn_state
            
            # --- 3. PROCESS GAME SELECTION ---
            if click_count > 0 and time.ticks_diff(current_time, last_click_time) > timeout_delay:
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
                
                if game_selection:
                    payload = {
                        "type": "GAME_SELECT",
                        "device_id": DEVICE_NAME,
                        "game": game_selection
                    }
                    try:
                        websocket.send(json.dumps(payload))
                        print("--> Sent request to server.")
                    except OSError:
                        print("\n[!] Connection lost during send. Reconnecting...")
                        websocket = connect_to_server()
                        websocket.send(json.dumps(payload))
                
                click_count = 0
                gc.collect()

        except Exception as master_e:
            print(f"\n[!] Network connection dropped: {master_e}. Reconnecting...")
            try: websocket.close()
            except: pass
            websocket = connect_to_server()

if __name__ == "__main__":
    set_led((50, 0, 0))
    main()
