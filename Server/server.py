from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import socket  
import random
import csv
import os
from datetime import datetime

app = FastAPI()

# --- CSV LOGGING SETUP ---
# Creates a 'data' folder in the same directory as server.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

def log_game_event(game_name: str, device_id: str, event_type: str, level: str = "N/A", status: str = "N/A", details: str = ""):
    """Appends game data to the respective game's CSV file."""
    filename = os.path.join(DATA_DIR, f"{game_name}.csv")
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as csvfile:
        fieldnames = ['Timestamp', 'Device ID', 'Event Type', 'Level Reached', 'Status', 'Details']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader() # Write column names if file is new
            
        writer.writerow({
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Device ID': device_id,
            'Event Type': event_type,
            'Level Reached': level,
            'Status': status,
            'Details': details
        })


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

manager = ConnectionManager()

# Stores the ongoing pattern for each device: {"ESP32_LEAD": ["red", "green", ...]}
game_states = {} 

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await manager.connect(device_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            
            if msg_type == "GAME_SELECT":
                game_selected = message.get("game")
                print(f"[SERVER] [!] {device_id} selected game: {game_selected}")
                
                if game_selected == "led_memory":
                    base_pattern = [random.choice(["red", "green", "yellow"]) for _ in range(10)]
                    game_states[device_id] = base_pattern 
                    
                    patterns = [base_pattern[:i+1] for i in range(10)]
                    print(f"[SERVER] Sending Levels 1-10 to {device_id}...")
                    
                    # LOGGING: Record that a new game started
                    log_game_event("led_memory", device_id, "GAME_START", level="1-10", status="PENDING", details="Sent initial batch")
                    
                    await websocket.send_text(json.dumps({
                        "type": "PATTERN", 
                        "patterns": patterns,
                        "start_level": 1
                    }))
                    
            elif msg_type == "GAME_RESULTS":
                results = message.get("results", [])
                device = message.get("device_id")
                
                print(f"\n[SERVER] [RESULTS] Received batch from {device}: {results}")
                
                if "loss" in results:
                    total_levels = len(game_states.get(device, [])) - 10 + len(results)
                    print(f"[SERVER] Game Over! {device} failed at Level {total_levels}.")
                    
                    # LOGGING: Record the game over state
                    log_game_event("led_memory", device, "GAME_OVER", level=str(total_levels), status="LOSS", details=str(results))
                    
                    if device in game_states:
                        del game_states[device]
                    print("[SERVER] Waiting for new game selection...\n")
                
                else:
                    old_pattern = game_states.get(device, [])
                    print(f"[SERVER] {device} beat Level {len(old_pattern)}! Generating next batch...")
                    
                    # LOGGING: Record the successful batch completion
                    log_game_event("led_memory", device, "BATCH_WIN", level=str(len(old_pattern)), status="WIN", details=str(results))
                    
                    new_additions = [random.choice(["red", "green", "yellow"]) for _ in range(10)]
                    new_base_pattern = old_pattern + new_additions
                    game_states[device] = new_base_pattern 
                    
                    start_level = len(old_pattern) + 1
                    patterns = [new_base_pattern[:i+1] for i in range(len(old_pattern), len(new_base_pattern))]
                    
                    print(f"[SERVER] Sending Levels {start_level}-{start_level+9} to {device}...")
                    
                    # LOGGING: Record the next batch being sent
                    log_game_event("led_memory", device, "NEXT_BATCH_SENT", level=f"{start_level}-{start_level+9}", status="PENDING")
                    
                    await websocket.send_text(json.dumps({
                        "type": "PATTERN", 
                        "patterns": patterns,
                        "start_level": start_level
                    }))
                
            else:
                print(f"[SERVER] [Data] from {device_id}: {message}")

    except WebSocketDisconnect:
        manager.disconnect(device_id)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    print("\n" + "="*55)
    print("  MINIGAMES HOST SERVER INITIALIZING...")
    print(f"  Detected Local IP : {local_ip}")
    print(f"  Data Directory    : {DATA_DIR}")
    print("="*55 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)