from pynput import keyboard
import requests, datetime

ENDPOINT = "http://localhost:8080/api/barcode/"
buffer = ""
_scan_callback = None
user_id = 0

def register_callback(fn):
    global _scan_callback
    _scan_callback = fn

def on_press(key):
    global buffer
    if key == keyboard.Key.enter and buffer:
        send(buffer)
        if _scan_callback:
            _scan_callback(buffer, user_id)
        buffer = ""
    else:
        try:
            buffer += key.char
        except AttributeError:
            pass  # Shift, Ctrl 등 무시

def send(code):
    data = {"code": code, "scannedAt": datetime.datetime.utcnow().isoformat()}
    print(data)
    url = ENDPOINT + code
    try:
        r = requests.get(url, json=data, timeout=3)
        r.raise_for_status()
        if r.headers.get("Content-Type", "").startswith("application/json"):
            global user_id
            user_id = r.json()
            print(r.json())
    except requests.RequestException as e:
        print("송신 실패:", e)

def listen():
    from pynput import keyboard
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    listen()