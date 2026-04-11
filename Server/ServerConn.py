import network
import time
import machine
import json
import gc
import uwebsockets
from neopixel import NeoPixel

from uwebsockets import client


# =========================================================
# DEPENDENCY CHECK & INSTALLATION
# =========================================================
def dependency_check():
    # 1. Connect to Wi-Fi FIRST so 'mip' has internet access
    #connect_wifi()

    # 2. Check for third-party packages and install if missing
    print("\nChecking required packages...")
    try:
        #import uwebsockets.client
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
            #import uwebsockets.client  # Import it now that it is installed
        except Exception as e:
            print(f"[X] Failed to install packages: {e}")
            set_led((50, 0, 0))
            while True: time.sleep(1)  # Halt execution if installation fails

# =========================================================

def connect_wifi(ssid, wifi_password):
    import minigames
    minigames.set_neo_color((50, 0, 0)) 
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(ssid, wifi_password)
        while not wlan.isconnected():
            time.sleep(0.5)
            print(".", end="")
    print("\nWiFi Connected! IP:", wlan.ifconfig()[0])

def connect_to_server(server_url):
    import minigames
    """Forces a connection loop until the server is reached."""
    while True:
        try:
            print(f"\nConnecting to Server: {server_url}")
            ws = uwebsockets.client.connect(server_url)
            ws.sock.setblocking(False)
            print("Server Connected!")
            minigames.set_neo_color((0, 50, 0))
            return ws
        except Exception as e:
            print(f"Failed to connect: {e}. Retrying in 3 seconds...")
            minigames.set_neo_color((50, 0, 0))
            time.sleep(3)
            
def poll_server(websocket, handle_game_selection):
    try:
        incoming_data = websocket.recv()

        if incoming_data:
            msg = json.loads(incoming_data)
            handle_game_selection(msg, websocket)

    except OSError:
        # No data available (this was already your behavior)
        pass

    except Exception as e:
        print(f"\n[!] Network error: {e}. Reconnecting...")
        return None  # signal reconnect needed

    return websocket

def send_game_selection(ws, game_selection, device_name):
    if not game_selection:
        return ws

    payload = {
        "type": "GAME_SELECT",
        "device_id": device_name,
        "game": game_selection
    }

    try:
        ws.send(json.dumps(payload))
        print(f"[GAME] Selected: {game_selection}")
    except OSError:
        print("\n[!] Connection lost. Reconnecting...")
        ws = connect_to_server()
        ws.send(json.dumps(payload))

    return ws

# def send(websocket, payload):
#     try:
#         websocket.send(json.dumps(payload))
#     except Exception as e:
#         print("Send failed:", e)
