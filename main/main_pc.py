import base64
import io
import logging
import sys
import os
import requests
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pydub import AudioSegment
from pydub.playback import play
import threading
import json
import smtplib
import keyboard

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SERVER_URL = "http://34.93.156.134:5000/web_server"

def send_request(service, req_type, params, email=None, phone=None):
    """Send request to the server and handle FUTURE_CALL polling."""
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
        response_json = response.json()
        # Handle FUTURE_CALL polling
        if req_type == "FUTURE_CALL" and response_json.get("status") == "IN_PROGRESS":
            request_id = response_json.get("request_id")
            logging.info(f"Request ID {request_id} is processing. Checking for results...")
            check_future_call_result(request_id, service, params)
        return response_json
    except requests.exceptions.RequestException as e:
        logging.error(f"RequestException: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None

def decode_and_play_audio(encoded_audio):
    """Decode Base64 encoded audio and play it."""
    try:
        logging.info("Decoding audio...")
        audio_bytes = base64.b64decode(encoded_audio)
        audio_buffer = io.BytesIO(audio_bytes)
        audio = AudioSegment.from_file(audio_buffer, format="wav")
        logging.info("Playing audio...")
        
        # Play audio in a separate thread to avoid blocking
        threading.Thread(target=play, args=(audio,)).start()
        logging.info("Audio playback started in a separate thread.")
    except Exception as e:
        logging.error(f"Error playing audio: {e}")
    finally:
        audio_buffer.close()
        logging.info("Audio buffer closed.")

def show_loud_Object(image, output_json):
    """
    Display the results of object detection.
    
    Args:
        output_json: JSON object containing detected objects and class labels.
    """
    try:
        results = json.loads(output_json)
        if results.get('status') != 'SUCCESS':
            logging.error(f"Error: {results.get('error')}")
            return
        
        detected_objects = results['detected_objects']
        annotated_image = image.copy()
        for obj in detected_objects:
            x, y, w, h = obj['bbox']['x'], obj['bbox']['y'], obj['bbox']['width'], obj['bbox']['height']
            class_name = obj['class']
            confidence = obj['confidence']
            color = obj['color']
            cv2.rectangle(annotated_image, (x, y), (x + w, y + h), color, 2)
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(annotated_image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        cv2.imshow('Annotated Image', annotated_image)
        cv2.waitKey(1)
        
        text_json = {"text": class_name}
        output_json = send_request("text_to_speech", "INLINE", text_json)
        #logging.info(output_json)
        if output_json['status'] == "SUCCESS":
            logging.info("Playing audio now...")
            decode_and_play_audio(output_json['data'])
    except Exception as e:
        logging.error(f"Failed to display results: {str(e)}")

def fetch_images_from_camera():
    """Continuously fetch images from the camera and process them."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logging.error("Failed to open camera.")
        return
    
    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                logging.error("Failed to capture image from camera.")
                continue
            
            # Encode the frame as base64
            _, buffer = cv2.imencode('.jpg', frame)
            image_b64 = base64.b64encode(buffer).decode('utf-8')
            
            # Create the sub_json object with image data
            image_json = {"image_b64": image_b64}
            
            output_json = send_request("ObjDetection", "INLINE", image_json)
            if output_json and output_json['status'] == "SUCCESS":
                logging.info("Received successful response from ObjDetection.")
                show_loud_Object(frame, output_json['data'])
            else:
                logging.error(f"Failed to get a successful response: {output_json}")
        except Exception as e:
            logging.error(f"Unexpected error in fetch_images_from_camera: {str(e)}")
            break
    
    cap.release()
    cv2.destroyAllWindows()
    logging.info("Camera released and windows destroyed.")

# Start the image fetching thread
image_thread = threading.Thread(target=fetch_images_from_camera)
image_thread.start()

def send_emergency_email():
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = 'ammu201995@gmail.com'
    sender_password = 'msaphdugxxbjyztw' # Use app-specific password if 2FA is enabled
    recipient_email = 'rodriguz3071@gmail.com'
    subject = 'Emergency Alert'
    body = 'This is an emergency message.'
    email_message = f"Subject: {subject}\n\n{body}"
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, email_message)
            logging.info("Emergency email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        logging.error("Failed to authenticate. Check your email and password.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

keyboard.add_hotkey('e', send_emergency_email)
logging.info("Press 'E' to send an emergency email.")
keyboard.wait('esc')