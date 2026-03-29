from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import socket  

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        print(f"[SERVER] [+] Node Connected: {device_id}")

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            print(f"[SERVER] [-] Node Disconnected: {device_id}")

    # We will keep the broadcast function defined for when we bring the UI back later, 
    # but we won't call it in the endpoint.
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await manager.connect(device_id, websocket)
    
    # [SILENCED] Do not send the CONNECT packet back to the ESP32
    # await manager.broadcast({"type": "CONNECT", "device_id": device_id})
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Print incoming game selection messages to the terminal
            if message.get("type") == "GAME_SELECT":
                print(f"[SERVER] [!] {device_id} selected game: {message.get('game')}")
            else:
                print(f"[SERVER] [Data] from {device_id}: {message}")

            # [SILENCED] Do not echo data back to the ESP32
            # await manager.broadcast(message)
            
    except WebSocketDisconnect:
        manager.disconnect(device_id)
        # [SILENCED] Do not broadcast disconnects
        # await manager.broadcast({"type": "DISCONNECT", "device_id": device_id})

def get_local_ip():
    """Detects the local IP address of the machine running the server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable, just forces the OS to route a packet
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    import uvicorn
    
    # --- IP Detection & Printout ---
    local_ip = get_local_ip()
    print("\n" + "="*55)
    print("  MINIGAMES HOST SERVER INITIALIZING...")
    print(f"  Detected Local IP : {local_ip}")
    print(f"  MicroPython URL   : ws://{local_ip}:8000/ws/ESP32_LEAD")
    print("="*55 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)