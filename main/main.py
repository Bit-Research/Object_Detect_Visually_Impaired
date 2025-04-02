import base64
import io
import logging
import requests
import numpy as np
import json
import smtplib
import threading
from pydub import AudioSegment
from pydub.playback import play
import RPi.GPIO as GPIO
from picamera import PiCamera2
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SERVER_URL = "http://34.93.156.134:5000/web_server"

# Create a lock for audio playback
audio_lock = threading.Lock()

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
        with audio_lock:
            play(audio)
        logging.info("Audio playback completed.")
    except Exception as e:
        logging.error(f"Error playing audio: {e}")
    finally:
        audio_buffer.close()
        logging.info("Audio buffer closed.")

def loud_Object(image, output_json):
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
            text_json = {"text": class_name}
            output_json = send_request("text_to_speech", "INLINE", text_json)
            if output_json['status'] == "SUCCESS":
                logging.info("Playing audio now...")
                threading.Thread(target=decode_and_play_audio, args=(output_json['data'],)).start()
    except Exception as e:
        logging.error(f"Failed to display results: {str(e)}")

def fetch_images_from_camera():
    """Continuously fetch images from the camera and process them."""
    camera = PiCamera2()
    camera.configure(camera.create_preview_configuration())

    # Start the camera
    camera.start() 
    
    while True:
        try:
            # Capture an image
            frame = camera.capture_array()

            # Convert the frame to a PIL image
            image = Image.fromarray(frame)
          
            # Encode the image as base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            image_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Create the sub_json object with image data
            image_json = {"image_b64": image_b64}
            
            output_json = send_request("ObjDetection", "INLINE", image_json)
            if output_json and output_json['status'] == "SUCCESS":
                logging.info("Received successful response from ObjDetection.")
                loud_Object(frame, output_json['data'])
            else:
                logging.error(f"Failed to get a successful response: {output_json}")
            
            raw_capture.truncate(0)
        except Exception as e:
            logging.error(f"Unexpected error in fetch_images_from_camera: {str(e)}")
            break
    
    camera.stop()
    camera.close()
    logging.info("Camera released.")

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

# Setup GPIO for emergency button
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def emergency_button_callback(channel):
    send_emergency_email()

GPIO.add_event_detect(18, GPIO.FALLING, callback=emergency_button_callback, bouncetime=300)
logging.info("Press the emergency button to send an emergency email.")

try:
    while True:
        pass
except KeyboardInterrupt:
    GPIO.cleanup()
    logging.info("GPIO cleanup done.")