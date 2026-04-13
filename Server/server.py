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
    filename = os.path.join(DATA_DIR, f"{game_name}.csv")
    file_exists = os.path.isfile(filename)

    with open(filename, mode='a', newline='') as csvfile:
        fieldnames = ['Timestamp', 'Device ID', 'Event Type', 'Level Reached', 'Status', 'Details']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

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

# ---------------- LED MEMORY STATE ----------------
game_states = {}

# ---------------- RPS STATE ----------------
rps_waiting = []  # players waiting for a match
# match_id -> {"players": [p1, p2], "selections": {}}
rps_matches = {}
# device_id -> match_id
rps_player_match = {}


def add_to_rps_queue(device_id: str):
    if device_id not in manager.active_connections:
        return
    if device_id in rps_player_match:
        return
    if device_id not in rps_waiting:
        rps_waiting.append(device_id)
        print(f"[SERVER][RPS] {device_id} added to queue.")


def remove_from_rps_queue(device_id: str):
    while device_id in rps_waiting:
        rps_waiting.remove(device_id)


async def send_json(device_id: str, payload: dict):
    ws = manager.active_connections.get(device_id)
    if ws:
        await ws.send_text(json.dumps(payload))


async def try_start_rps_match():
    # Remove stale queue entries first
    valid_waiting = []
    seen = set()
    for device_id in rps_waiting:
        if device_id in seen:
            continue
        if device_id not in manager.active_connections:
            continue
        if device_id in rps_player_match:
            continue
        valid_waiting.append(device_id)
        seen.add(device_id)
    rps_waiting[:] = valid_waiting

    if len(rps_waiting) < 2:
        return

    # Random draw from whoever is connected and waiting
    p1, p2 = random.sample(rps_waiting, 2)
    rps_waiting.remove(p1)
    rps_waiting.remove(p2)

    match_id = f"rps_{random.randint(1000, 9999)}"
    while match_id in rps_matches:
        match_id = f"rps_{random.randint(1000, 9999)}"

    rps_matches[match_id] = {
        "players": [p1, p2],
        "selections": {}
    }
    rps_player_match[p1] = match_id
    rps_player_match[p2] = match_id

    print(f"[SERVER][RPS] Match found: {match_id} -> {p1} vs {p2}")

    await send_json(p1, {
        "type": "RPS_READY",
        "game_id": match_id,
        "message": "Opponent found! Start round.",
        "opponent": p2
    })
    await send_json(p2, {
        "type": "RPS_READY",
        "game_id": match_id,
        "message": "Opponent found! Start round.",
        "opponent": p1
    })

    log_game_event("rock_paper_scissors", p1, "MATCH_START", status="READY", details=f"{match_id} vs {p2}")
    log_game_event("rock_paper_scissors", p2, "MATCH_START", status="READY", details=f"{match_id} vs {p1}")



def determine_rps_result(sel1, sel2):
    # Handles forfeit explicitly
    if sel1 == "forfeit" and sel2 == "forfeit":
        return "tie"
    if sel1 == "forfeit":
        return "player2_win"
    if sel2 == "forfeit":
        return "player1_win"

    if sel1 == sel2:
        return "tie"

    wins = {
        "rock": "scissors",
        "paper": "rock",
        "scissors": "paper"
    }
    return "player1_win" if wins[sel1] == sel2 else "player2_win"


async def cleanup_rps_player(device_id: str):
    remove_from_rps_queue(device_id)

    match_id = rps_player_match.pop(device_id, None)
    if not match_id:
        return

    match = rps_matches.pop(match_id, None)
    if not match:
        return

    players = match.get("players", [])
    other = None
    for p in players:
        if p != device_id:
            other = p
            break

    if other:
        rps_player_match.pop(other, None)
        if other in manager.active_connections:
            print(f"[SERVER][RPS] {device_id} left {match_id}. Re-queueing {other}.")
            await send_json(other, {
                "type": "RPS_WAITING",
                "message": "Opponent disconnected. Waiting for a new opponent..."
            })
            add_to_rps_queue(other)
            await try_start_rps_match()


async def process_rps_selection(device_id: str, selection: str):
    if selection not in {"rock", "paper", "scissors", "forfeit"}:
        await send_json(device_id, {
            "type": "RPS_ERROR",
            "message": "Invalid selection. Use rock, paper, scissors, or forfeit."
        })
        return

    match_id = rps_player_match.get(device_id)
    if not match_id or match_id not in rps_matches:
        await send_json(device_id, {
            "type": "RPS_ERROR",
            "message": "No active RPS match found."
        })
        return

    match = rps_matches[match_id]
    if device_id in match["selections"]:
        await send_json(device_id, {
            "type": "RPS_ERROR",
            "message": "Selection already received for this round."
        })
        return

    match["selections"][device_id] = selection
    print(f"[SERVER][RPS] {device_id} selected {selection} in {match_id}")

    if len(match["selections"]) < 2:
        await send_json(device_id, {
            "type": "RPS_WAITING",
            "message": "Selection received. Waiting for opponent..."
        })
        return

    p1, p2 = match["players"]
    s1 = match["selections"].get(p1)
    s2 = match["selections"].get(p2)
    result = determine_rps_result(s1, s2)

    if result == "tie":
        p1_result = "tie"
        p2_result = "tie"
    elif result == "player1_win":
        p1_result = "win"
        p2_result = "lose"
    else:
        p1_result = "lose"
        p2_result = "win"

    await send_json(p1, {
        "type": "RPS_RESULT",
        "result": p1_result,
        "game_id": match_id,
        "opponent_selection": s2
    })
    await send_json(p2, {
        "type": "RPS_RESULT",
        "result": p2_result,
        "game_id": match_id,
        "opponent_selection": s1
    })

    print(f"[SERVER][RPS] {match_id}: {p1}({s1}) vs {p2}({s2}) -> {result}")

    log_game_event("rock_paper_scissors", p1, "ROUND_COMPLETE", status=p1_result.upper(), details=f"{match_id}: you={s1}, opp={p2}:{s2}")
    log_game_event("rock_paper_scissors", p2, "ROUND_COMPLETE", status=p2_result.upper(), details=f"{match_id}: you={s2}, opp={p1}:{s1}")

    # End this match after one round. Winner can select RPS again later.
    rps_matches.pop(match_id, None)
    rps_player_match.pop(p1, None)
    rps_player_match.pop(p2, None)


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

                    patterns = [base_pattern[:i + 1] for i in range(10)]
                    print(f"[SERVER] Sending Levels 1-10 to {device_id}...")

                    log_game_event("led_memory", device_id, "GAME_START", level="1-10", status="PENDING", details="Sent initial batch")

                    await websocket.send_text(json.dumps({
                        "type": "PATTERN",
                        "patterns": patterns,
                        "start_level": 1
                    }))

                elif game_selected == "rps":
                    add_to_rps_queue(device_id)
                    log_game_event("rock_paper_scissors", device_id, "QUEUE_JOIN", status="WAITING")
                    await send_json(device_id, {
                        "type": "RPS_WAITING",
                        "message": "Waiting for opponent..."
                    })
                    await try_start_rps_match()

            elif msg_type == "RPS_SELECTION":
                selection = message.get("selection")
                if selection:
                    await process_rps_selection(device_id, selection)

            elif msg_type == "GAME_RESULTS":
                results = message.get("results", [])
                device = message.get("device_id")

                print(f"\n[SERVER] [RESULTS] Received batch from {device}: {results}")

                if "loss" in results:
                    total_levels = len(game_states.get(device, [])) - 10 + len(results)
                    print(f"[SERVER] Game Over! {device} failed at Level {total_levels}.")

                    log_game_event("led_memory", device, "GAME_OVER", level=str(total_levels), status="LOSS", details=str(results))

                    if device in game_states:
                        del game_states[device]
                    print("[SERVER] Waiting for new game selection...\n")

                else:
                    old_pattern = game_states.get(device, [])
                    print(f"[SERVER] {device} beat Level {len(old_pattern)}! Generating next batch...")

                    log_game_event("led_memory", device, "BATCH_WIN", level=str(len(old_pattern)), status="WIN", details=str(results))

                    new_additions = [random.choice(["red", "green", "yellow"]) for _ in range(10)]
                    new_base_pattern = old_pattern + new_additions
                    game_states[device] = new_base_pattern

                    start_level = len(old_pattern) + 1
                    patterns = [new_base_pattern[:i + 1] for i in range(len(old_pattern), len(new_base_pattern))]

                    print(f"[SERVER] Sending Levels {start_level}-{start_level + 9} to {device}...")

                    log_game_event("led_memory", device, "NEXT_BATCH_SENT", level=f"{start_level}-{start_level + 9}", status="PENDING")

                    await websocket.send_text(json.dumps({
                        "type": "PATTERN",
                        "patterns": patterns,
                        "start_level": start_level
                    }))

            else:
                print(f"[SERVER] [Data] from {device_id}: {message}")

    except WebSocketDisconnect:
        manager.disconnect(device_id)
        await cleanup_rps_player(device_id)


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
    print("\n" + "=" * 55)
    print("  MINIGAMES HOST SERVER INITIALIZING...")
    print(f"  Detected Local IP : {local_ip}")
    print(f"  Data Directory    : {DATA_DIR}")
    print("=" * 55 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
