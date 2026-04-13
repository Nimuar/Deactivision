import minigames as mg
from time import sleep
import time
import json

########## ROCK PAPER SCISSORS ##########


def countdown_buzzer():
    # Rock
    mg.lcd_print("Rock...")
    mg.set_led("red")
    mg.beepSound(600, 0.2)
    sleep(0.5)
    mg.clear_led()

    # Paper
    mg.lcd_print("Paper...")
    mg.set_led("green")
    mg.beepSound(700, 0.2)
    sleep(0.5)
    mg.clear_led()

    # Scissors
    mg.lcd_print("Scissors...")
    mg.set_led("yellow")
    mg.beepSound(800, 0.2)
    sleep(0.5)
    mg.clear_led()

    # Shoot!
    mg.lcd_print("SHOOT!")
    mg.beepSound(1000, 0.3)
    sleep(0.2)
    mg.clear_led()


def get_player_selection(timeout_ms=5000):
    """
    Wait for one button press and return:
      rock / paper / scissors / forfeit
    """
    mg.red_button_cnt = 0
    mg.green_button_cnt = 0
    mg.yellow_button_cnt = 0

    start_time = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
        if mg.red_button_cnt > 0:
            mg.lcd_print("Rock!")
            mg.set_led("red")
            mg.beepSound(600, 0.2)
            sleep(0.3)
            mg.clear_led()
            return "rock"

        elif mg.green_button_cnt > 0:
            mg.lcd_print("Paper!")
            mg.set_led("green")
            mg.beepSound(700, 0.2)
            sleep(0.3)
            mg.clear_led()
            return "paper"

        elif mg.yellow_button_cnt > 0:
            mg.lcd_print("Scissors!")
            mg.set_led("yellow")
            mg.beepSound(800, 0.2)
            sleep(0.3)
            mg.clear_led()
            return "scissors"

        time.sleep_ms(10)

    mg.lcd_print("Forfeit!")
    return "forfeit"


def send_selection_to_server(selection, websocket, device_id):
    try:
        payload = {
            "type": "RPS_SELECTION",
            "device_id": device_id,
            "selection": selection,
        }
        websocket.send(json.dumps(payload))
        print("Sent selection to server:", selection)
        return True
    except Exception as e:
        print("Failed to send selection:", e)
        return False


def get_round_result(websocket, timeout_ms=8000):
    """
    Wait for server response after sending move.
    Handles:
      - RPS_WAITING
      - RPS_RESULT
      - RPS_ERROR
    """
    start_time = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
        try:
            incoming_data = websocket.recv()
            if incoming_data:
                msg = json.loads(incoming_data)
                msg_type = msg.get("type")

                if msg_type == "RPS_WAITING":
                    print(
                        "[RPS] Waiting:", msg.get("message", "Waiting for opponent...")
                    )

                elif msg_type == "RPS_RESULT":
                    print("[RPS] Result received:", msg)
                    return msg

                elif msg_type == "RPS_ERROR":
                    print("[RPS] Error:", msg.get("message", "Unknown RPS error"))
                    return {
                        "type": "RPS_ERROR",
                        "message": msg.get("message", "Unknown RPS error"),
                    }

        except OSError:
            pass

        time.sleep_ms(10)

    return {"type": "RPS_ERROR", "message": "Timeout waiting for round result"}


def show_round_result(result_msg):
    """
    Display server-decided round result on board.
    Expected keys:
      result, opponent_selection
    """
    result = result_msg.get("result", "error")
    opponent = result_msg.get("opponent_selection", "?")

    if result == "win":
        mg.lcd_print("You Win!")
        mg.set_led("green")
        mg.beepSound(1000, 0.3)
        sleep(1.5)

    elif result == "lose":
        mg.lcd_print("You Lose!")
        mg.set_led("red")
        mg.beepSound(400, 0.4)
        sleep(1.5)

    elif result == "tie":
        mg.lcd_print("Tie! Opp:" + str(opponent))
        mg.set_led("yellow")
        mg.beepSound(750, 0.25)
        sleep(1.5)

    else:
        mg.lcd_print("RPS Error")
        mg.set_led("red")
        sleep(1.5)

    mg.clear_led()


def wait_for_opponent(websocket):
    """Blocks until the server sends RPS_READY"""

    print("Waiting for opponent...")

    while True:
        try:
            incoming_data = websocket.recv()
            if incoming_data:
                msg = json.loads(incoming_data)
                if msg.get("type") == "RPS_READY":
                    print("[RPS] Match found! Starting...")
                    return True
                elif msg.get("type") == "RPS_WAITING":
                    pass
        except OSError:
            pass

        time.sleep_ms(10)


def RPS_player(websocket=None, device_id=None):
    """
    Play exactly ONE round of RPS, then return.
    ServerConn.py should call this each time it receives RPS_READY.
    """
    if websocket is None or device_id is None:
        print("RPS_player requires websocket and device_id")
        return

    match_found = wait_for_opponent(websocket)
    if not match_found:
        return

    countdown_buzzer()

    selection = get_player_selection()

    success = send_selection_to_server(selection, websocket, device_id)
    if not success:
        mg.lcd_print("Send Error")
        sleep(1.5)
        mg.clear_led()
        return

    if selection == "forfeit":
        mg.lcd_print("Forfeit Sent")
    else:
        mg.lcd_print("You chose: " + selection)

    sleep(1)

    result_msg = get_round_result(websocket)

    if result_msg.get("type") == "RPS_RESULT":
        show_round_result(result_msg)
    else:
        mg.lcd_print("Server Error")
        sleep(1.5)
        mg.clear_led()

    # Important: return after ONE round
    return


########## MAIN LOOP ##########

if __name__ == "__main__":
    countdown_buzzer()
    print(get_player_selection())
