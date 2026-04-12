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
            
            # Clean up any RPS games this device was in
            games_to_remove = []
            for game_id, game in rps_games.items():
                if device_id in game["players"]:
                    print(f"[SERVER] Removing {device_id} from RPS game {game_id}")
                    game["players"].remove(device_id)
                    if len(game["players"]) == 0:
                        games_to_remove.append(game_id)
            
            for game_id in games_to_remove:
                del rps_games[game_id]
                print(f"[SERVER] Removed empty RPS game {game_id}")

manager = ConnectionManager()

# Stores the ongoing pattern for each device: {"ESP32_LEAD": ["red", "green", ...]}
game_states = {} 

# Stores RPS game state: {"game_id": {"players": ["device1", "device2"], "selections": {"device1": "rock", "device2": "paper"}, "round": 1}}
rps_games = {}

def determine_rps_winner(selection1, selection2):
    """Determine the winner of a Rock Paper Scissors round"""
    if selection1 == selection2:
        return "tie"
    
    winning_moves = {
        "rock": "scissors",
        "paper": "rock", 
        "scissors": "paper"
    }
    
    if winning_moves[selection1] == selection2:
        return "player1_win"
    else:
        return "player2_win"

def create_rps_game(device_id):
    """Create a new RPS game for a device"""
    game_id = f"rps_{device_id}_{random.randint(1000, 9999)}"
    rps_games[game_id] = {
        "players": [device_id],
        "selections": {},
        "round": 1,
        "status": "waiting_for_players"
    }
    print(f"[SERVER] Created RPS game {game_id} for {device_id}")
    return game_id

def process_rps_selection(device_id, selection):
    """Process a player's RPS selection and determine round results"""
    # Find the game this device is in
    game_id = None
    for gid, game in rps_games.items():
        if device_id in game["players"]:
            game_id = gid
            break
    
    if not game_id:
        print(f"[SERVER] No active RPS game found for {device_id}")
        return
    
    game = rps_games[game_id]
    game["selections"][device_id] = selection
    
    print(f"[SERVER] {device_id} selected {selection} in game {game_id}")
    
    # Check if all players have made selections
    if len(game["selections"]) == len(game["players"]):
        # All players have selected, determine winner
        players = game["players"]
        if len(players) == 2:
            selection1 = game["selections"][players[0]]
            selection2 = game["selections"][players[1]]
            
            result = determine_rps_winner(selection1, selection2)
            
            # Send results to both players
            for i, player in enumerate(players):
                player_result = "win" if (result == "tie" or 
                                        (result == "player1_win" and i == 0) or 
                                        (result == "player2_win" and i == 1)) else "lose"
                
                if result == "tie":
                    player_result = "tie"
                
                # Send result to player
                websocket = manager.active_connections.get(player)
                if websocket:
                    try:
                        websocket.send_text(json.dumps({
                            "type": "RPS_RESULT",
                            "result": player_result,
                            "round": game["round"],
                            "opponent_selection": selection2 if i == 0 else selection1
                        }))
                        print(f"[SERVER] Sent {player_result} to {player}")
                    except Exception as e:
                        print(f"[SERVER] Failed to send result to {player}: {e}")
            
            # Log the round
            log_game_event("rock_paper_scissors", device_id, "ROUND_COMPLETE", 
                         level=str(game["round"]), status=result, 
                         details=f"{players[0]}: {selection1} vs {players[1]}: {selection2}")
            
            # Prepare for next round
            game["round"] += 1
            game["selections"] = {}
            
        elif len(players) == 1:
            selection1 = game["selections"][players[0]]
            ai_choice = random.choice(["rock", "paper", "scissors"])
            result = determine_rps_winner(selection1, ai_choice)
            player_result = "tie" if result == "tie" else ("win" if result == "player1_win" else "lose")

            websocket = manager.active_connections.get(players[0])
            if websocket:
                try:
                    websocket.send_text(json.dumps({
                        "type": "RPS_RESULT",
                        "result": player_result,
                        "round": game["round"],
                        "opponent_selection": ai_choice
                    }))
                    print(f"[SERVER] Sent {player_result} to {players[0]} against AI")
                except Exception as e:
                    print(f"[SERVER] Failed to send AI result to {players[0]}: {e}")

            log_game_event("rock_paper_scissors", device_id, "ROUND_COMPLETE",
                         level=str(game["round"]), status=result,
                         details=f"{players[0]}: {selection1} vs AI: {ai_choice}")
            game["round"] += 1
            game["selections"] = {}
        else:
            print(f"[SERVER] RPS game {game_id} doesn't have exactly 2 players")
    else:
        print(f"[SERVER] Waiting for {len(game['players']) - len(game['selections'])} more selections in game {game_id}")

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
                    
                elif game_selected == "rps":
                    # Create new RPS game for this device
                    game_id = create_rps_game(device_id)
                    
                    # For now, assume single-player mode or waiting for another player
                    # In a real implementation, you'd match players or have a lobby system
                    print(f"[SERVER] {device_id} joined RPS game {game_id}")
                    
                    # LOGGING: Record RPS game start
                    log_game_event("rock_paper_scissors", device_id, "GAME_START", level="1", status="WAITING", details=f"Game ID: {game_id}")
                    
                    # Send confirmation to player
                    await websocket.send_text(json.dumps({
                        "type": "RPS_READY",
                        "game_id": game_id,
                        "message": "Waiting for opponent..."
                    }))
                    
            elif msg_type == "RPS_SELECTION":
                selection = message.get("selection")
                if selection:
                    process_rps_selection(device_id, selection)
                    
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