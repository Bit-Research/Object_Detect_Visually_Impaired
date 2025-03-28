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
        response_json = response.json()

        # Handle FUTURE_CALL polling
        if req_type == "FUTURE_CALL" and response_json.get("status") == "IN_PROGRESS":
            request_id = response_json.get("request_id")
            logging.info(f"Request ID {request_id} is processing. Checking for results...")
            check_future_call_result(request_id, service, params)
        return response_json
    except requests.exceptions.RequestException as e:
        logging.error(f"Error: {e}")
        return None

def image_to_json(image):
    """
    Convert an image to a JSON object with RGB pixel data.
    
    Args:
        image: Input image
    
    Returns:
        JSON object containing image data in RGB format
    """
    try:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Get image dimensions
        height, width, _ = image_rgb.shape
        
        # Create a list to hold pixel data
        pixels = [{"r": int(r), "g": int(g), "b": int(b)} for row in image_rgb for r, g, b in row]
        
        # Create the JSON object
        image_json = {
            "width": width,
            "height": height,
            "pixels": pixels
        }
        
        return image_json
    except Exception as e:
        logging.error(f"Failed to convert image to JSON: {str(e)}")
        return None

def decode_and_play_audio(encoded_audio):
    """Decode Base64 encoded audio and play it."""
    try:
        audio_bytes = base64.b64decode(encoded_audio)
        audio_buffer = io.BytesIO(audio_bytes)
        
        # Load and play audio
        audio = AudioSegment.from_file(audio_buffer, format="wav")
        play(audio)
    except Exception as e:
        logging.error(f"Error playing audio: {e}")
    finally:
        audio_buffer.close()

def show_loud_Object(image, output_json):
    """
    Display the results of object detection.
    
    Args:
        output_json: JSON object containing detected objects and class labels.
    """
    try:
        # Parse the JSON object
        results = json.loads(output_json)
        
        # Check status
        if results.get('status') != 'SUCCESS':
            logging.error(f"Error: {results.get('error')}")
            return
        
        detected_objects = results['detected_objects']
        
        # Draw bounding boxes and labels
        annotated_image = image.copy()
        for obj in detected_objects:
            x, y, w, h = obj['bbox']['x'], obj['bbox']['y'], obj['bbox']['width'], obj['bbox']['height']
            class_name = obj['class']
            confidence = obj['confidence']
            color = obj['color']
            
            # Draw rectangle
            cv2.rectangle(annotated_image, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(annotated_image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Display the image using OpenCV
        cv2.imshow('Annotated Image', annotated_image)
        cv2.waitKey(1)  # Display the image for 1 millisecond
        
        # Create the JSON object
        text_json = {
            "text": class_name
        }
        output_json = send_request("text_to_speech", "INLINE", text_json)
        logging.info(output_json)
        if output_json['status'] == "SUCCESS":
            logging.info("Playing audio now...")
            decode_and_play_audio(output_json['data'])
    except Exception as e:
        logging.error(f"Failed to display results: {str(e)}")
        
def fetch_images_from_camera():
    """Continuously fetch images from the camera and process them."""
    cap = cv2.VideoCapture(0)  # Open the default camera
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.error("Failed to capture image from camera.")
            continue
        
        image_json = image_to_json(frame)
        output_json = send_request("ObjDetection", "INLINE", image_json)
        logging.info(output_json)
        if output_json['status'] == "SUCCESS":
            show_loud_Object(frame, output_json['data'])

    cap.release()

# Start the image fetching thread
image_thread = threading.Thread(target=fetch_images_from_camera)
image_thread.start()

### Separate Thread for Emergency Email

import smtplib
import keyboard

def send_emergency_email():
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    sender_email = 'ammu201995@gmail.com'
    sender_password = 'msaphdugxxbjyztw'  # Use app-specific password if 2FA is enabled
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