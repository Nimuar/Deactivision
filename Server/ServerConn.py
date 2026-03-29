import network
import time
import machine
import json
import gc
from neopixel import NeoPixel
import uwebsockets.client

# --- Hardware Setup for Adafruit ESP32 Feather V2 ---
PIN_NEO_PWR = 2
PIN_NEO_DATA = 0
neo_pwr = machine.Pin(PIN_NEO_PWR, machine.Pin.OUT)
neo_pwr.value(1)
np = NeoPixel(machine.Pin(PIN_NEO_DATA), 1)

# GPIO38 is an Input-Only pin. Adafruit provides a physical pull-up resistor for it.
btn = machine.Pin(38, machine.Pin.IN)

# --- Configuration ---
WIFI_SSID = "ATTXvnW88k"
WIFI_PASS = "t846j?v2jrvk"
SERVER_URL = "ws://192.168.1.69:8000/ws/ESP32_LEAD" 

def set_led(color):
    np[0] = color
    np.write()

def connect_wifi():
    set_led((50, 0, 0)) # Dim Red
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
            print(".", end="")
    print("\nWiFi Connected! IP:", wlan.ifconfig()[0])

def main():
    connect_wifi()
    
    websocket = None
    try:
        print(f"Connecting to Server: {SERVER_URL}")
        websocket = uwebsockets.client.connect(SERVER_URL)
        
        # Force the socket to never wait/block ---
        websocket.sock.setblocking(False)
        
        print("Server Connected!")
        set_led((0, 50, 0))
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        set_led((50, 0, 0))
        return

    click_count = 0
    last_click_time = 0
    timeout_delay = 1000
    last_btn_state = 1  

    print("Listening for button clicks...")
    
    while True:
        try:
            # 1. YIELD TO OS
            time.sleep_ms(10)
            current_time = time.ticks_ms()
            
            # 2. NON-BLOCKING NETWORK READ
            try:
                incoming_data = websocket.recv()
                if incoming_data:
                    print(f"\n[SERVER -> ESP32]: {incoming_data}")
            except OSError:
                # Expected behavior when no data is available in non-blocking mode
                pass
            except Exception as e:
                print(f"Network error during read: {e}")
                set_led((50, 0, 0))
                break 
            
            # 3. BUTTON EDGE DETECTION
            current_btn_state = btn.value()
            
            if current_btn_state == 0 and last_btn_state == 1:
                if time.ticks_diff(current_time, last_click_time) > 50:
                    click_count += 1
                    last_click_time = current_time
                    print(f"Click! (Count: {click_count})")
                    
            last_btn_state = current_btn_state
            
            # 4. PROCESS GAME SELECTION
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
                        "device_id": "ESP32_LEAD",
                        "game": game_selection
                    }
                    try:
                        websocket.send(json.dumps(payload))
                        print("--> Sent to server.")
                    except OSError:
                        print("Connection lost during send.")
                        set_led((50, 0, 0))
                        break
                
                # Reset count and clean memory regardless of valid/invalid input
                click_count = 0
                gc.collect()

        except Exception as master_e:
            # If anything catastrophically fails in the loop, print it so we know!
            print(f"CRITICAL LOOP ERROR: {master_e}")
            break

if __name__ == "__main__":
    set_led((50, 0, 0))
    main()