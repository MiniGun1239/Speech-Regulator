import os
import threading # Import the threading module
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.core.window import Window

from core.stt_engine import STTEngine
from core.classifier import HateSpeechClassifier
from core.response_handler import ResponseHandler


# Get the directory of the current script
script_dir = os.path.dirname(__file__)

# Join the script's directory with the relative path to the .kv file
kv_file_path = os.path.join(script_dir, 'ui', 'main.kv')

# --- Debugging: Print the path and add try-except for Builder loading ---
print(f"Kivy is attempting to load KV file from: {kv_file_path}")
try:
    Builder.load_file(kv_file_path)
    print(f"Successfully loaded KV file: {kv_file_path}")
except Exception as e:
    print(f"ERROR: Failed to load KV file '{kv_file_path}'. Reason: {e}")
    # You might want to display a simple error message on screen here too
    # For now, we'll let the fallback Label handle the blank screen if this fails.


class MainLayout(BoxLayout):
    pass


class SpeechRegulatorApp(App):
    def build(self):
        self.title = "Speech Regulator"
        
        # --- Set a default window size to ensure visibility ---
        Window.size = (400, 600) # Set a reasonable width and height for the window
        print(f"Kivy Window size set to: {Window.size}")

        # --- Debugging: Check if MainLayout can be instantiated after Builder.load_file ---
        try:
            self.root_widget = MainLayout()
            print("Successfully instantiated MainLayout.")
        except Exception as e:
            print(f"ERROR: Failed to instantiate MainLayout. Reason: {e}")
            # Fallback to a simple Label if MainLayout instantiation fails
            # This helps confirm if the Kivy environment is working at all.
            return Label(text=f"Error loading UI: {e}\nCheck console for details.", markup=True)
        
        # Init modules
        self.classifier = HateSpeechClassifier()
        self.response = ResponseHandler()
        # Ensure STTEngine duration matches the polling interval or is slightly longer
        self.stt = STTEngine(enabled=False, duration=1.5) 

        # Keep track of the STT thread
        self._stt_thread = None
        self._stt_is_processing = False # Flag to prevent starting multiple STT threads simultaneously

        # Poll mic every 0.75s to check if a new STT process can be started
        Clock.schedule_interval(self._loop, 0.75) 
        return self.root_widget

    def _loop(self, dt):
        """
        Main application loop, scheduled by Kivy Clock.
        Checks if STT is enabled and if a transcription is not already in progress.
        If conditions are met, it starts a new transcription in a separate thread.
        """
        if self.stt.enabled and not self._stt_is_processing:
            self._start_listening_thread()

    def _start_listening_thread(self):
        """
        Starts the STT engine's listen method in a separate thread.
        This prevents the UI from freezing during recording and transcription.
        """
        self._stt_is_processing = True
        self._stt_thread = threading.Thread(target=self._run_stt_and_process)
        self._stt_thread.daemon = True # Allow the main program to exit even if thread is running
        self._stt_thread.start()

    def _run_stt_and_process(self):
        """
        Method executed by the STT thread.
        Calls the blocking listen method and then processes the text.
        """
        text = self.stt.listen()
        if text:
            # UI updates MUST be done on the main thread using Clock.schedule_once
            Clock.schedule_once(lambda dt: self._handle_text(text))
        
        # Reset the flag when processing is complete
        self._stt_is_processing = False

    def process_manual_input(self, text):
        """
        Handles text input manually (e.g., from TextInput widget).
        """
        self._handle_text(text)

    def toggle_listen(self):
        """
        Toggles the microphone listening state.
        """
        self.stt.enabled = not self.stt.enabled
        if hasattr(self.root_widget, 'ids') and 'status_label' in self.root_widget.ids:
            self.root_widget.ids.status_label.text = (
                "[color=00ff00]Listening...[/color]" if self.stt.enabled else "[color=aaaaaa]Stopped[/color]"
            )
        # If stopping listening, ensure any active thread is signaled to stop (if implemented in STTEngine)
        # For this blocking STTEngine, we simply wait for the current cycle to finish.

    def _handle_text(self, text: str):
        """
        Processes the transcribed text (from mic or manual input) and updates the UI.
        This method is now always called on the main Kivy thread.
        """
        if hasattr(self.root_widget, 'ids'):
            if 'transcribed_text' in self.root_widget.ids:
                self.root_widget.ids.transcribed_text.text = f"Detected: {text}"
            
            scores = self.classifier.predict(text)
            is_hate = self.classifier.is_hate_speech_from_scores(scores)

            # Pretty print top scores
            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            if 'score_text' in self.root_widget.ids:
                self.root_widget.ids.score_text.text = " | ".join(f"{k}:{v:.2f}" for k, v in top)

            if is_hate:
                self.response.trigger_alert(text, scores)
                if 'status_label' in self.root_widget.ids:
                    self.root_widget.ids.status_label.text = "[color=ff0000]Hate/Toxic detected![/color]"
            else:
                if 'status_label' in self.root_widget.ids:
                    self.root_widget.ids.status_label.text = "[color=00ff00]Clean[/color]"


if __name__ == "__main__":
    SpeechRegulatorApp().run()
