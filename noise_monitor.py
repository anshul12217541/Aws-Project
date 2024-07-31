from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import pyaudio
import numpy as np
import json
import time
import os

# AWS IoT Core details
aws_endpoint = "a3d33zf04vlyhm-ats.iot.ap-south-1.amazonaws.com"  # Replace with your actual AWS IoT endpoint
client_id = "NoiseSensor"
thing_name = "NoiseSensor"
topic = "noise/sensor"  # Define the topic

# Path to certificates
ca_path = "C:/project/NoisePollutionMonitoring/AmazonRootCA1.pem"
cert_path = "C:/project/NoisePollutionMonitoring/certificate.pem.crt"
key_path = "C:/project/NoisePollutionMonitoring/0f1bf3ecad7fbdbbc562f1aef1f2e10a9aded649f2afb54c9b5534508d924ad7-private.pem.key"

# Verify file paths
print("Directory contents:", os.listdir("C:/project/NoisePollutionMonitoring/"))
print("CA Path:", ca_path)
print("Certificate Path:", cert_path)
print("Key Path:", key_path)

# Initialize MQTT shadow client
shadow_client = AWSIoTMQTTShadowClient(client_id)
shadow_client.configureEndpoint(aws_endpoint, 8883)
shadow_client.configureCredentials(ca_path, key_path, cert_path)

# Connect to AWS IoT Core
shadow_client.connect()

# Create a device shadow handler
device_shadow = shadow_client.createShadowHandlerWithName(thing_name, True)

# PyAudio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 1

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Start Recording
stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

print("Recording...")

def get_rms(data):
    """ Calculate Root Mean Square (RMS) for a given data array """
    count = len(data) // 2
    shorts = np.frombuffer(data, dtype=np.int16)
    sum_squares = np.sum(np.square(shorts))
    return np.sqrt(sum_squares / count)

def update_shadow_callback(payload, responseStatus, token):
    print(f"Shadow update response: {responseStatus}")

try:
    while True:
        data = stream.read(CHUNK)
        rms = get_rms(data)
        dB = 20 * np.log10(rms)

        # Publish to AWS IoT Core
        message = json.dumps({"noise": dB})
        shadow_client.getMQTTConnection().publish(topic, message, 1)
        
        # Update device shadow
        shadow_state = {
            "state": {
                "reported": {
                    "noise": dB
                }
            }
        }
        device_shadow.shadowUpdate(json.dumps(shadow_state), update_shadow_callback, 5)
        
        print(f"Noise Level: {dB:.2f} dB")
        time.sleep(RECORD_SECONDS)

except KeyboardInterrupt:
    print("Recording stopped")

# Stop Recording
stream.stop_stream()
stream.close()
audio.terminate()
shadow_client.disconnect()
