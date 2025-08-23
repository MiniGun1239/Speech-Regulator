import csv
import os
import time
from kivy.core.audio import SoundLoader

class ResponseHandler:
    """
    Handles logging of detected hate speech events and triggering audio alerts.
    It creates a log directory and a CSV file to record events, and plays an
    alert sound when hate speech is detected.
    """
    def __init__(self, log_dir="logs", alert_sound_path="ui/assets/alert.wav"):
        """
        Initializes the ResponseHandler.
        Args:
            log_dir (str): The directory where event logs will be stored.
            alert_sound_path (str): The file path to the alert sound.
        """
        self.log_dir = log_dir
        self.csv_path = os.path.join(self.log_dir, "events.csv")
        self.alert_sound = None  # Initialize to None

        # Ensure the log directory exists
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            print(f"[ResponseHandler] Log directory ensured: {self.log_dir}")
        except OSError as e:
            print(f"[ResponseHandler ERROR] Could not create log directory {self.log_dir}: {e}")
            # The application can still run, but logging might fail.

        # Attempt to load the alert sound
        try:
            # Ensure the alert sound path is absolute for robustness
            absolute_sound_path = os.path.abspath(alert_sound_path)
            if not os.path.exists(absolute_sound_path):
                print(f"[ResponseHandler WARNING] Alert sound file not found: {absolute_sound_path}")
            else:
                self.alert_sound = SoundLoader.load(absolute_sound_path)
                if not self.alert_sound:
                    print(f"[ResponseHandler WARNING] Failed to load alert sound from {absolute_sound_path}.")
                else:
                    print(f"[ResponseHandler] Alert sound loaded from: {absolute_sound_path}")
        except Exception as e:
            print(f"[ResponseHandler ERROR] Error loading alert sound: {e}")

        # Initialize CSV file if it doesn't exist
        if not os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["timestamp", "text", "top_scores"])
                print(f"[ResponseHandler] Created new log file: {self.csv_path}")
            except IOError as e:
                print(f"[ResponseHandler ERROR] Could not create CSV log file {self.csv_path}: {e}")
        else:
            print(f"[ResponseHandler] Existing log file found: {self.csv_path}")


    def trigger_alert(self, text: str, scores: dict):
        """
        Triggers an alert (audio beep, sound playback) and logs the event.
        Args:
            text (str): The detected text that triggered the alert.
            scores (dict): A dictionary of classification scores for the text.
        """
        # --- Sound feedback (works on many terminals); ignore if it fails ---
        # This is a basic system beep and might not work on all platforms or environments.
        try:
            os.system("printf '\\a'")
        except Exception:
            pass # Suppress errors if system beep fails

        # Play the loaded alert sound if available
        if self.alert_sound:
            try:
                self.alert_sound.play()
            except Exception as e:
                print(f"[ResponseHandler ERROR] Failed to play alert sound: {e}")

        # --- Log the event to CSV ---
        # Sort scores to get the top 3 labels for logging
        top_scores_formatted = []
        if scores:
            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            top_scores_formatted = [f"{k}:{v:.2f}" for k, v in top]

        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([current_timestamp, text, "; ".join(top_scores_formatted)])
            # print(f"[ResponseHandler] Logged event: '{text}' at {current_timestamp}") # Optional: detailed log
        except IOError as e:
            print(f"[ResponseHandler ERROR] Failed to write to CSV log file {self.csv_path}: {e}")
        except Exception as e:
            print(f"[ResponseHandler ERROR] An unexpected error occurred during logging: {e}")
