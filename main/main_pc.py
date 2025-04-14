import base64
import io
import json
import logging
import smtplib
import threading
import time
import cv2
import keyboard

import requests
import numpy as np
from PIL import Image
from pydub import AudioSegment
from pydub.playback import play

# --- CONFIGURATION ---

SERVER_URL = "http://34.93.156.134:5000/web_server"
EMAIL_SENDER = 'ammu201995@gmail.com'
EMAIL_PASSWORD = 'msaphdugxxbjyztw'
EMAIL_RECEIVER = 'rodriguz3071@gmail.com'

event = threading.Event()
audio_lock = threading.Lock()
frame_lock = threading.Lock()

# OpenCV Camera Setup
camera = cv2.VideoCapture(0)

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- UTILS ---

def get_frame():
    with frame_lock:
        ret, frame = camera.read()
        return frame if ret else None

def encode_image(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)
    buffered = io.BytesIO()
    pil_image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def send_request(service, req_type, params, email=None, phone=None):
    payload = {
        "service_name": service,
        "sub_json": params,
        "request_type": req_type
    }
    if email:
        payload["mail_id"] = email
    if phone:
        payload["phone_no"] = phone

    try:
        response = requests.post(SERVER_URL, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Request failed: {e}")
    return None

def decode_and_play_audio(encoded_audio):
    try:
        audio_bytes = base64.b64decode(encoded_audio)
        with io.BytesIO(audio_bytes) as audio_buffer:
            audio = AudioSegment.from_file(audio_buffer, format="wav")
            with audio_lock:
                play(audio)
    except Exception as e:
        logging.error(f"Error playing audio: {e}")

def loud_object(image, output_json):
    try:
        results = json.loads(output_json)
        if results.get('status') != 'SUCCESS':
            logging.error(f"Detection error: {results.get('error')}")
            return

        for obj in results['detected_objects']:
            text_json = {"text": obj['class']}
            response = send_request("text_to_speech", "INLINE", text_json)
            if response and response['status'] == "SUCCESS" and response['data']:
                decode_and_play_audio(response['data'])

    except Exception as e:
        logging.error(f"Failed to process object detection: {e}")

def fetch_images_from_camera():
    while True:
        frame = get_frame()
        if frame is not None:
            cv2.imshow("Live Camera", frame)
            cv2.waitKey(1)  # Non-blocking wait
        time.sleep(0.03)

def trigger_object_detection():
    while True:
        if keyboard.is_pressed("o"):  # Press 'o' to trigger object detection
            frame = get_frame()
            if frame is None:
                continue
            image_b64 = encode_image(frame)
            response = send_request("ObjDetection", "INLINE", {"image_b64": image_b64})
            if response and response['status'] == "SUCCESS" and response['data']:
                loud_object(frame, response['data'])
            else:
                logging.error("Object detection failed or empty response.")
            time.sleep(1)  # Prevent multiple triggers

def trigger_text_ocr():
    while True:
        if keyboard.is_pressed("t"):  # Press 't' to trigger OCR
            frame = get_frame()
            if frame is None:
                continue
            image_b64 = encode_image(frame)
            response = send_request("ocr_detect", "INLINE", {"image_b64": image_b64})
            if response and response['status'] == "SUCCESS" and response['data']:
                tts_response = send_request("text_to_speech", "INLINE", {"text": response['data']})
                if tts_response and tts_response['status'] == "SUCCESS" and tts_response['data']:
                    decode_and_play_audio(tts_response['data'])
                else:
                    logging.error("TTS failed or empty.")
            else:
                logging.error("OCR failed or empty response.")
            time.sleep(1)

def send_emergency_email():
    subject = 'Emergency Alert'
    body = 'This is an emergency message.'
    email_message = f"Subject: {subject}\n\n{body}"

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, email_message)
            logging.info("Emergency email sent successfully!")
    except Exception as e:
        logging.error(f"Failed to send emergency email: {e}")

def emergency_monitor():
    while True:
        if keyboard.is_pressed("e"):  # Press 'e' to send emergency email
            send_emergency_email()
            time.sleep(1)

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    try:
        # Start all threads
        threading.Thread(target=fetch_images_from_camera, daemon=True).start()
        threading.Thread(target=trigger_object_detection, daemon=True).start()
        threading.Thread(target=trigger_text_ocr, daemon=True).start()
        threading.Thread(target=emergency_monitor, daemon=True).start()

        logging.info("System initialized. Press 'o' for object detection, 't' for OCR, 'e' for emergency email.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        camera.release()
        cv2.destroyAllWindows()
        logging.info("System shutdown. Camera released.")
