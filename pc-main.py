import socket
import threading
import tempfile
import os
from vosk import Model, KaldiRecognizer
import json

HOST = ''  # Listen on all interfaces
PORT = 50007

rolling_buffer = []  # store last 2 audio files as bytes

# Load Vosk model once at startup
vosk_model = Model("model")  # Path to your Vosk model directory

def vosk_hate_detector(audio_bytes):
    # Vosk expects PCM 16kHz mono WAV data (no header)
    # If your audio is not in this format, you must convert it before using Vosk
    rec = KaldiRecognizer(vosk_model, 16000)
    rec.AcceptWaveform(audio_bytes)
    result = rec.Result()
    text = json.loads(result).get("text", "").lower()
    # Simple hate speech keyword detection (replace with real logic)
    hate_keywords = ["hate", "kill", "violence"]
    return any(word in text for word in hate_keywords)

def handle_client(conn, addr):
    global rolling_buffer
    print(f"Connected by {addr}")

    try:
        # Receive length
        length_bytes = conn.recv(4)
        if not length_bytes:
            conn.close()
            return
        length = int.from_bytes(length_bytes, 'big')

        # Receive audio data
        audio_data = b''
        while len(audio_data) < length:
            packet = conn.recv(length - len(audio_data))
            if not packet:
                break
            audio_data += packet

        # Update rolling buffer (keep last 2 chunks)
        rolling_buffer.append(audio_data)
        if len(rolling_buffer) > 2:
            rolling_buffer.pop(0)

        # Hate speech detection using Vosk
        flag = vosk_hate_detector(audio_data)

        # Send back flag as 1 or 0 byte
        conn.sendall(b'1' if flag else b'0')

        # Save last 2 chunks if flagged
        if flag:
            print("Hate speech detected! Saving last 2 chunks...")
            for i, chunk in enumerate(rolling_buffer):
                filename = os.path.join(tempfile.gettempdir(), f"chunk_{i}.wav")
                with open(filename, 'wb') as f:
                    f.write(chunk)
                print(f"Saved {filename}")

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print("Server listening...")

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    main()
