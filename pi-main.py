import sounddevice as sd
import soundfile as sf
import subprocess
import socket
import os
import numpy as np

SERVER_IP = '192.168.1.100'  # replace with your PC's actual IP address
SERVER_PORT = 50007
CHUNK_DURATION = 5  # seconds
FILENAME = 'chunk.wav'

def record_audio(filename, duration=5, fs=16000):
    print("Recording...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    # Ensure audio is 2D for soundfile
    if audio.ndim == 1:
        audio = np.expand_dims(audio, axis=1)
    sf.write(filename, audio, fs, subtype='PCM_16')
    print("Recorded and saved:", filename)

def send_file(filename):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_IP, SERVER_PORT))
        with open(filename, 'rb') as f:
            data = f.read()
            s.sendall(len(data).to_bytes(4, 'big') + data)
            # receive bool response (1 byte)
            flag = s.recv(1)
    return flag

def main():
    while True:
        record_audio(FILENAME, CHUNK_DURATION)
        flag = send_file(FILENAME)
        flag_str = flag.decode('utf-8') if flag else 'None'
        print(f"Flag received: {flag_str} ({'Hate speech detected' if flag == b'1' else 'Clean audio'})")

        # Clean up the file after sending
        try:
            os.remove(FILENAME)
        except Exception as e:
            print(f"Error removing file: {e}")
        # The server is expected to return b'1' for hate speech detected, b'0' for clean audio.
        if flag == b'1':
            print("Hate speech detected! Turn on red light.")
        elif flag == b'0':
            print("Clean audio.")
        else:
            print(f"Unexpected flag received: {flag!r}")
        # Optional: trigger LED here based on flag
        if flag == b'1':
            print("Hate speech detected! Turn on red light.")
        else:
            print("Clean audio.")

if __name__ == "__main__":
    main()
