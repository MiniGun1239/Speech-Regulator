import csv
import os
import time
import sys # For resource path handling
import logging # Import the logging module

# --- Kivy imports ---
from kivy.core.audio import SoundLoader

class ResponseHandler:
    """
    Handles logging of detected hate speech events and triggering audio alerts.
    It creates a log directory and a CSV file to record events, and plays an
    alert sound when hate speech is detected.
    """
    def __init__(self, log_dir="logs", alert_sound_path="ui/assets/alert.wav", resource_path_func=None): # Removed app_logger
        """
        Initializes the ResponseHandler.
        Args:
            log_dir (str): The directory where event logs will be stored.
            alert_sound_path (str): The file path to the alert sound.
            resource_path_func (callable): A function to resolve paths for bundled resources.
        """
        self.resource_path_func = resource_path_func if resource_path_func else (lambda x: x) # Use provided func or identity
        self.logger = logging.getLogger("SpeechRegulator") # Use the globally configured logger

        # log_dir should be relative to the executable's current working directory,
        # not necessarily inside the bundle.
        # This log_dir is not a bundled resource, so it does not use resource_path_func.
        self.log_dir = log_dir
        self.csv_path = os.path.join(self.log_dir, "events.csv")
        self.alert_sound = None  # Initialize to None

        # Ensure the log directory exists
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            self.logger.info(f"[ResponseHandler] Log directory ensured: {self.log_dir}")
        except OSError as e:
            self.logger.error(f"[ResponseHandler ERROR] Could not create log directory {self.log_dir}: {e}")
            # The application can still run, but logging might fail.

        # Attempt to load the alert sound using the resource_path_func helper
        try:
            # The alert_sound_path should be relative to the _MEIPASS root (e.g., 'ui/assets/alert.wav')
            # It's important that this matches how you added it in main.spec 'datas'.
            full_alert_sound_path = self.resource_path_func(alert_sound_path)
            
            self.logger.debug(f"[ResponseHandler Debug] Attempting to load alert sound from: {full_alert_sound_path}")

            if not os.path.exists(full_alert_sound_path):
                self.logger.warning(f"[ResponseHandler WARNING] Alert sound file not found: {full_alert_sound_path}")
            else:
                self.alert_sound = SoundLoader.load(full_alert_sound_path)
                if not self.alert_sound:
                    self.logger.warning(f"[ResponseHandler WARNING] Failed to load alert sound from {full_alert_sound_path}.")
                else:
                    self.logger.info(f"[ResponseHandler] Alert sound loaded from: {full_alert_sound_path}")
        except Exception as e:
            self.logger.error(f"[ResponseHandler ERROR] Error loading alert sound: {e}")

        # Initialize CSV file if it doesn't exist
        if not os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    # Removed "source" from CSV header
                    writer.writerow(["timestamp", "text", "top_scores"]) 
                self.logger.info(f"[ResponseHandler] Created new log file: {self.csv_path}")
            except IOError as e:
                self.logger.error(f"[ResponseHandler ERROR] Could not create CSV log file {self.csv_path}: {e}")
        else:
            self.logger.info(f"[ResponseHandler] Existing log file found: {self.csv_path}")


    def trigger_alert(self, text: str, scores: dict): # Removed source parameter
        """
        Triggers an alert (audio beep, sound playback) and logs the event.
        Args:
            text (str): The detected text that triggered the alert.
            scores (dict): A dictionary of classification scores for the text.
        """
        # Define current_timestamp before its first use in print statement
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"[ResponseHandler] Alert triggered and event logged at {current_timestamp}")

        # Play the loaded alert sound if available
        if self.alert_sound:
            try:
                self.alert_sound.play()
            except Exception as e:
                self.logger.error(f"[ResponseHandler ERROR] Failed to play alert sound: {e}")

        # --- Log the event to CSV ---
        # Sort scores to get the top 3 labels for logging
        top_scores_formatted = []
        if scores:
            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            top_scores_formatted = [f"{k}:{v:.2f}" for k, v in top]

        try:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Removed source from CSV row
                writer.writerow([current_timestamp, text, "; ".join(top_scores_formatted)]) 
        except IOError as e:
            self.logger.error(f"[ResponseHandler ERROR] Failed to write to CSV log file {self.csv_path}: {e}")
        except Exception as e:
            self.logger.error(f"[ResponseHandler ERROR] An unexpected error occurred during logging: {e}")
