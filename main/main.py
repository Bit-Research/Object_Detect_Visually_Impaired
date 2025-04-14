import base64
import io
import json
import logging
import smtplib
import threading
import time

import numpy as np
import requests
from PIL import Image
from pydub import AudioSegment
from pydub.playback import play
from picamera2 import Picamera2
import RPi.GPIO as GPIO

# --- CONFIGURATION ---

SERVER_URL = "http://34.93.156.134:5000/web_server"
EMAIL_SENDER = 'ammu201995@gmail.com'
EMAIL_PASSWORD = 'msaphdugxxbjyztw'
EMAIL_RECEIVER = 'rodriguz3071@gmail.com'

TRIG, ECHO = 22, 23
EMERGENCY_PIN, OCR_PIN = 18, 19

event = threading.Event()
audio_lock = threading.Lock()

# --- GPIO SETUP ---

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.setup(EMERGENCY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(OCR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- CAMERA SETUP ---

camera = Picamera2()
camera.configure(camera.create_preview_configuration())
camera.start()
frame_lock = threading.Lock()

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- UTILS ---

def get_distance():
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.5)

    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG, GPIO.LOW)

    while GPIO.input(ECHO) == GPIO.LOW:
        pulse_start = time.time()
    while GPIO.input(ECHO) == GPIO.HIGH:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = round(pulse_duration * 17150, 2)
    return distance

def get_frame():
    with frame_lock:
        return camera.capture_array()

def encode_image(image):
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
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
    except requests.exceptions.RequestException as e:
        logging.error(f"RequestException: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    return None

def decode_and_play_audio(encoded_audio):
    try:
        logging.info("Decoding and playing audio...")
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
            logging.error(f"Object Detection Error: {results.get('error')}")
            return

        for obj in results['detected_objects']:
            text_json = {"text": obj['class']}
            response = send_request("text_to_speech", "INLINE", text_json)
            if response and response['status'] == "SUCCESS":
                decode_and_play_audio(response['data'])

    except Exception as e:
        logging.error(f"Failed to process object detection: {e}")

def fetch_images_from_camera():
    try:
        while True:
            event.wait()
            frame = get_frame()
            image = Image.fromarray(frame)
            image_b64 = encode_image(image)

            response = send_request("ObjDetection", "INLINE", {"image_b64": image_b64})
            if response and response['status'] == "SUCCESS":
                loud_object(frame, response['data'])
            else:
                logging.error(f"Object Detection failed: {response}")

            event.clear()

    except Exception as e:
        logging.error(f"Error in fetch_images_from_camera: {e}")
    finally:
        camera.stop()
        camera.close()
        logging.info("Camera stopped and closed.")

def fetch_text_from_camera(_=None):
    try:
        frame = get_frame()
        image = Image.fromarray(frame)
        image_b64 = encode_image(image)

        response = send_request("ocr_detect", "INLINE", {"image_b64": image_b64})
        logging.info(f"Received from OCR {response}")
        if response and response['status'] == "SUCCESS" and response['data']:
            tts_response = send_request("text_to_speech", "INLINE", {"text": response['data']})
            if tts_response and tts_response['status'] == "SUCCESS":
                decode_and_play_audio(tts_response['data'])
            else:
                logging.error(f"TTS failed: {tts_response}")
        else:
            logging.error(f"OCR failed: {response}")
    except Exception as e:
        logging.error(f"Error in fetch_text_from_camera: {e}")

def monitor_object_distance():
    try:
        while True:
            distance = get_distance()
            logging.info(f"Distance: {distance} cm")
            if distance < 10:
                logging.info("Object detected!")
                event.set()
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()

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

def emergency_button_callback(channel):
    send_emergency_email()

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    setup_gpio()

    GPIO.add_event_detect(EMERGENCY_PIN, GPIO.FALLING, callback=emergency_button_callback, bouncetime=300)
    GPIO.add_event_detect(OCR_PIN, GPIO.FALLING, callback=fetch_text_from_camera, bouncetime=300)

    image_thread = threading.Thread(target=fetch_images_from_camera)
    distance_thread = threading.Thread(target=monitor_object_distance)

    image_thread.start()
    distance_thread.start()

    logging.info("System initialized. Waiting for input...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()
        logging.info("System terminated and GPIO cleaned up.")
