# Minigames - Network & Server Architecture

## Overview
The Minigames project utilizes a distributed network architecture to support real-time, multiplayer embedded system gameplay. The system operates on a Star Topology, routing all client communication through a central host server. This document outlines the server infrastructure, communication protocols, and edge-device networking logic.

## Architecture Topology
Instead of establishing peer-to-peer connections among the game controllers, the system relies on a central Host Server. 
* **The Host Server:** A central machine (Raspberry Pi 4 / Local PC) that manages game state, matchmaking, and routing.
* **The Edge Nodes:** Adafruit ESP32 Feather V2 microcontrollers acting as physical game controllers. These nodes process hardware inputs (buttons, potentiometers) and transmit data to the host.

## Communication Layer: WebSockets
Standard HTTP requests introduce excessive overhead (TCP handshakes, headers) that cause latency in fast-paced multiplayer interactions. To achieve the required responsiveness, the system utilizes **WebSockets**. 

Once an ESP32 node initializes a connection to the server, the TCP connection remains persistent. This full-duplex channel allows bi-directional JSON payload transmission with near-zero latency, which is critical for reaction-based mechanics like Rock Paper Scissors or continuous-input tracking in Wavelength.

In the example MicroPython code, there is this line:
`SERVER_URL = "ws://192.168.1.69:8000/ws/ESP32_LEAD"`
Because the board connects using that specific URL, the server extracts ESP32_LEAD, saves it to the dictionary, and says, "Okay, from now on, any data coming from this socket belongs to ESP32_LEAD."

#### **How to set up the other 6 boards?**
You can name them whatever makes sense for your hardware layout:
- Board 2: `SERVER_URL = "ws://.../ws/ESP32_PLAYER_1"`
- Board 3: `SERVER_URL = "ws://.../ws/ESP32_PLAYER_2"`
- Board 4: `SERVER_URL = "ws://.../ws/ESP32_PLAYER_3"`
- etc..

## The Host Server (Backend)
The backend infrastructure is built to be asynchronous and lightweight.

* **Framework:** FastAPI (Python) running via the Uvicorn ASGI server.
* **Connection Management:** The server maintains a dictionary of active WebSocket connections, assigning unique device IDs to each node upon connection.
* **Packet Routing:** Incoming JSON payloads are parsed and routed based on the requested action. For example, a `GAME_SELECT` payload directs the server to initialize a specific game state machine.
* **Auto-IP Detection:** On startup, the server dynamically detects and broadcasts its local IPv4 address, simplifying the configuration process for the edge devices on dynamic local networks.

### Standard Packet Structure
Data is standardized into compact JSON payloads to minimize parsing overhead on the microcontrollers.

**Client to Server (Action):**
```json
{
  "type": "GAME_SELECT",
  "device_id": "ESP32_LEAD",
  "game": "wavelength"
}
```

### Edge Device Networking (MicroPython Client)

The game controllers handle physical inputs and transmit data efficiently to prevent network saturation and CPU starvation.

---

### Network Stability & Initialization

Upon boot, the device connects to the local WLAN. An onboard NeoPixel provides visual network status:

- 🔴 Red = Connecting/Error  
- 🟢 Green = Connected  

To prevent the microcontroller from freezing while waiting for TCP acknowledgments, the WebSocket is forced into a non-blocking state:

```python
websocket.sock.setblocking(False)
``` 
This allows the main FreeRTOS loop to execute continuously even if the network buffer is empty.

### Input Processing & Edge Detection
Physical button presses are debounced in software. Logic is triggered exclusively on state changes (edge detection) to ensure single physical interactions do not register as multiple inputs.

### Resource & Power Management
Microcontrollers running continuous network loops are susceptible to crashes and excessive power draw. The software addresses this through three mechanisms:

- **CPU Yielding:** A minor delay (`time.sleep_ms(10)`) is injected into the main loop, yielding processing time back to the underlying FreeRTOS Wi-Fi stack to prevent silent disconnects.

- **Memory Management:** Manual garbage collection (`gc.collect()`) executes immediately after JSON payload transmission to prevent RAM fragmentation.

- **Low Power Mode:** To conserve energy, the edge devices transition to a low-power sleep mode when no one has been playing the games for a certain period of time (no inputs received). This distributes the power-state logic to the clients rather than relying on server-side timeouts.

### Dependencies & Installation
To run the host server, specific Python packages are required. Create a `requirements.txt` file in the root server directory containing the following packages:

```Python
fastapi
uvicorn[standard]
websockets
```

To install the necessary packages and start the server, run the following commands in the terminal:
```python
# Install the required packages
pip install -r requirements.txt

# Start the server
python server.py
```

### MicroPython Environment Setup (Thonny)
The ESP32 microcontrollers require specific libraries to handle WebSocket communication. These must be installed directly onto the board's flash memory using Thonny's REPL and the MicroPython package manager (`mip`).

1. **Connect the Board to Wi-Fi**
```Python
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('YOUR_WIFI_NAME', 'YOUR_WIFI_PASSWORD')
```
2. **Install Dependencies via `mip`**
Run the following commands in the REPL to install the standard logging module and the WebSocket client.

```Python
import mip

# Install the lightweight MicroPython logging module
mip.install("logging")

# Install the uwebsockets client directly to the /lib directory
mip.install("[https://raw.githubusercontent.com/danni/uwebsockets/master/uwebsockets/client.py](https://raw.githubusercontent.com/danni/uwebsockets/master/uwebsockets/client.py)", target="/lib/uwebsockets")
mip.install("[https://raw.githubusercontent.com/danni/uwebsockets/master/uwebsockets/protocol.py](https://raw.githubusercontent.com/danni/uwebsockets/master/uwebsockets/protocol.py)", target="/lib/uwebsockets")
```

