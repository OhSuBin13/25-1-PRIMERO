# -*- coding: utf-8 -*-
import os, time, datetime, subprocess
import requests
import numpy as np
import cv2
import tflite_runtime.interpreter as tflite
from requests_toolbelt import MultipartEncoder
from pynput import keyboard
from gpiozero import AngularServo, Device
from gpiozero.pins.pigpio import PiGPIOFactory

Device.pin_factory = PiGPIOFactory()

SERVO_PIN = 17
servo = AngularServo(SERVO_PIN, min_angle=0, max_angle=180)


# 서보 객체 생성 (min_angle, max_angle은 서보에 따라 -90~90, 0~180 등 조정 가능)


def set_servo_angle(angle):
    servo.angle = angle
    time.sleep(0.35)

IMG_DIR = "captures"
TFLITE_PATH = "/home/prim/ras_test_01/best.tflite"
API_ROOT = "http://localhost:8080/api/v1/recycles"

os.makedirs(IMG_DIR, exist_ok=True)

def analyze_with_tflite(img_path):
    interpreter = tflite.Interpreter(model_path=TFLITE_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    image = cv2.imread(img_path)
    ih, iw = input_details[0]['shape'][1:3]
    image_resized = cv2.resize(image, (iw, ih))
    img_input = np.expand_dims(image_resized, axis=0).astype(np.float32) / 255.0
    interpreter.set_tensor(input_details[0]['index'], img_input)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])[0]
    # conf*class_score > 0.4이면 OK
    for out in output:
        conf = out[4]
        class_score = out[5]
        if conf * class_score > 0.4:
            return "OK"
    return "NG"

def control_servo(result):
    try:
        if result == "OK":
            print("서보: 시계방향 80°")
            set_servo_angle(80)
            time.sleep(0.7)
            set_servo_angle(0)
        else:
            print("서보: 반시계 80°")
            set_servo_angle(100)
            time.sleep(0.7)
            set_servo_angle(0)
    except Exception as e:
        print("서보 오류:", e)

def post_recycle_log(user_id, photo_file, result):
    url = f"{API_ROOT}/{user_id}"
    m = MultipartEncoder(fields={
        'photo': (photo_file, open(photo_file, "rb"), 'image/jpeg'),
        'result': str(result)
    })
    headers = {'Content-Type': m.content_type}
    try:
        res = requests.post(url, headers=headers, data=m, timeout=5)
        print(f"✅ 업로드: {photo_file} {result}")
    except Exception as e:
        print("❌ 업로드 실패:", e)

def process_scan(barcode_value, user_id):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    img = f"{IMG_DIR}/{ts}.jpg"
    print(f"[{ts}] 2초 대기 후 촬영…")
    time.sleep(2)
    subprocess.run(["libcamera-still", "-o", img, "--nopreview", "-t", "500"], check=True)
    print("📷  촬영 완료:", img)
    result = analyze_with_tflite(img)
    print(f"YOLO 결과: {result}")
    control_servo(result)
    if user_id:
        post_recycle_log(user_id, img, result)
    else:
        print("userId 없음 → 업로드 생략")

# USB 바코드 스캐너 이벤트
ENDPOINT = "http://localhost:8080/api/barcode/"
buffer = ""
user_id = 0

def send_barcode(code):
    global user_id
    data = {"code": code, "scannedAt": datetime.datetime.utcnow().isoformat()}
    print(data)
    url = ENDPOINT + code
    try:
        r = requests.get(url, json=data, timeout=3)
        r.raise_for_status()
        if r.headers.get("Content-Type", "").startswith("application/json"):
            user_id = r.json()
            print("user_id:", user_id)
    except requests.RequestException as e:
        print("송신 실패:", e)

def on_press(key):
    global buffer
    if key == keyboard.Key.enter and buffer:
        send_barcode(buffer)
        if user_id:
            process_scan(buffer, user_id)
        buffer = ""
    else:
        try:
            buffer += key.char
        except AttributeError:
            pass

def listen():
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    try:
        listen()
    finally:
        # gpiozero는 별도의 cleanup 필요 없음
        servo.detach()   # 서보 PWM 신호 끊기
