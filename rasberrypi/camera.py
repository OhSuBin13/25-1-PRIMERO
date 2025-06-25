# camera.py
# import time, subprocess, datetime
import time, datetime, cv2
import barcode
import requests
import os
from requests_toolbelt import MultipartEncoder

IMG_DIR = "captures"
API_ROOT = "http://localhost:8080/api/v1/recycles"
os.makedirs(IMG_DIR, exist_ok=True)

def post_recycle_log(user_id: int, photo_file:str):
    url   = f"{API_ROOT}/{user_id}"
    m = MultipartEncoder(fields={'photo': (photo_file, open(photo_file, "rb"), 'image/jpeg')})
    headers = {'Content-Type' : m.content_type}
    res = requests.post(url, headers=headers, data=m)

    # files = {"photo": open(photo_file, "rb")} if photo_file else {}
    # try:
    #     res = requests.post(url, files=files, timeout=10)
    #     res.raise_for_status()
    #     print("✅", url, res.status_code, photo_file)
    # except requests.RequestException as e:
    #     print("❌", e)
    # finally:
    #     if files:
    #         files["photo"].close()

def shoot_and_send(user_id: int, barcode: str):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    img = f"{IMG_DIR}/{ts}.jpg"
    print(f"[{ts}] 5초 대기 후 촬영…")
    time.sleep(5)
    # ──★ libcamera-still (Pi 카메라) 예시 ──────────────────
    # subprocess.run(["libcamera-still", "-o", img, "--nopreview", "-t", "100"],
    #                check=True)
    # print("📷  촬영 완료:", img)

    cam = cv2.VideoCapture(1, cv2.CAP_DSHOW)   # 윈도우 기본 웹캠
    ret, frame = cam.read()
    cam.release()
    if ret:
        cv2.imwrite(img, frame)
        print('📷  저장:', img)
    else:
        print('⚠️  카메라 캡처 실패')

    post_recycle_log(user_id, img)

def after_scan(barcode_value, user_id):
    if user_id:
        shoot_and_send(user_id, barcode_value)
    else:
        print("userId 없음 → 업로드 생략")

if __name__ == "__main__":
    # ① barcode 모듈에 shoot 콜백을 등록
    barcode.register_callback(after_scan)
    # ② 바코드 리스너 실행(블로킹)
    barcode.listen()