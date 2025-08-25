import os
import threading
import csv # For reading log files
import sys # For resource path handling
import datetime # Import datetime for formatting timestamps
import logging # Import the logging module

# --- Centralized Logging Setup ---
# Determine base dir (script or .exe)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else os.path.dirname(sys.executable)

# Logs folder
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True) # Ensure logs directory exists
LOG_FILE = os.path.join(LOG_DIR, "logs.txt")

# Create logger
logger = logging.getLogger("SpeechRegulator")
logger.setLevel(logging.DEBUG)  # Or INFO/WARNING for less verbosity

# Only add handler if not already added (avoids duplicates when app rebuilds or reloads)
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

logger.info("Logger initialized (file-only).")


# --- Kivy imports ---
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout

# --- Custom module imports (will be passed the resource_path_func) ---
from core.stt_engine import STTEngine
from core.classifier import HateSpeechClassifier
from core.response_handler import ResponseHandler

# Helper function to get the correct path for bundled resources in PyInstaller
def _get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    This function should be the single source of truth for resource paths.
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        logger.debug(f"[ResourcePath Debug] Running FROZEN (PyInstaller). base_path: {base_path}")
    else:
        base_path = BASE_DIR # Use the globally defined BASE_DIR
        logger.debug(f"[ResourcePath Debug] Running as SCRIPT. base_path: {base_path}")
    
    resolved_path = os.path.join(base_path, relative_path)
    logger.debug(f"[ResourcePath Debug] Resolving '{relative_path}' -> final: '{resolved_path}'")
    return resolved_path


# Join the script's directory with the relative path to the .kv file
kv_file_path = _get_resource_path(os.path.join('ui', 'main.kv'))


class MainLayout(BoxLayout):
    pass


class SpeechRegulatorApp(App):
    def build(self):
        self.title = "Speech Regulator"
        
        # Assign the globally configured logger to the app instance
        self.logger = logger 
        self.logger.info("SpeechRegulatorApp build method started.")
        # Renamed PROJECT_ROOT_DIR to BASE_DIR here for consistency
        self.logger.info(f"PROJECT_ROOT_DIR (dev mode): {BASE_DIR}") 
        self.logger.info(f"Application log file created at: {LOG_FILE}")


        # --- Debugging: Print the path and add try-except for Builder loading ---
        self.logger.info(f"Kivy is attempting to load KV file from: {kv_file_path}")
        try:
            Builder.load_file(kv_file_path)
            self.logger.info(f"Successfully loaded KV file: {kv_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to load KV file '{kv_file_path}'. Reason: {e}")
            # Fallback to a simple Label if Builder loading fails
            return Label(text=f"Error loading UI: {e}\nCheck console for details.", markup=True)

        # --- Set a default window size to ensure visibility ---
        Window.size = (450, 800) # Set to (450, 800) as per your new code
        self.logger.info(f"Kivy Window size set to: {Window.size}")

        # --- Debugging: Check if MainLayout can be instantiated after Builder.load_file ---
        try:
            self.root_widget = MainLayout()
            self.logger.info("Successfully instantiated MainLayout.")
        except Exception as e:
            self.logger.error(f"Failed to instantiate MainLayout. Reason: {e}")
            # Fallback to a simple Label if MainLayout instantiation fails
            return Label(text=f"Error loading UI: {e}\nCheck console for details.", markup=True)
        
        # Init modules, they will now get the logger globally via logging.getLogger("SpeechRegulator")
        self.classifier = HateSpeechClassifier(resource_path_func=_get_resource_path)
        self.response = ResponseHandler(resource_path_func=_get_resource_path)
        # Ensure STTEngine duration matches the polling interval or is slightly longer
        self.stt = STTEngine(enabled=False, duration=1.5) 

        # Keep track of the STT thread
        self._stt_thread = None
        self._stt_is_processing = False # Flag to prevent starting multiple STT threads simultaneously

        self.log_popup_instance = None # To hold a reference to the active popup if needed

        # Poll mic every 0.75s to check if a new STT process can be started
        Clock.schedule_interval(self._loop, 0.75) 
        return self.root_widget


    def on_start(self):
        self.logger.info("[App] No explicit layout update scheduled on start (buttons are now fine).")


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
        Args:
            text (str): The input text.
        """
        if hasattr(self.root_widget, 'ids'):
            if 'transcribed_text' in self.root_widget.ids:
                self.root_widget.ids.transcribed_text.text = f"Detected: {text}"
            
            scores = self.classifier.predict(text)
            is_hate = self.classifier.is_hate_speech_from_scores(scores)

            # Pretty print top scores
            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            if hasattr(self.root_widget, 'ids') and 'score_text' in self.root_widget.ids:
                self.root_widget.ids.score_text.text = " | ".join(f"{k}:{v:.2f}" for k, v in top)

            if is_hate:
                self.response.trigger_alert(text, scores) 
                if hasattr(self.root_widget, 'ids') and 'status_label' in self.root_widget.ids:
                    self.root_widget.ids.status_label.text = "[color=ff0000]Hate/Toxic detected![/color]"
            else:
                if hasattr(self.root_widget, 'ids') and 'status_label' in self.root_widget.ids:
                    self.root_widget.ids.status_label.text = "[color=00ff00]Clean[/color]"


    def read_log_file(self):
        """Reads the events.csv log file and returns its content as a list of dictionaries."""
        log_entries = []
        try:
            # Use the ResponseHandler's csv_path to ensure correct file location
            log_file_path = self.response.csv_path 
            if not os.path.exists(log_file_path):
                self.logger.info(f"[Log Viewer] Log file not found: {log_file_path}")
                return log_entries

            with open(log_file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    log_entries.append(row)
            return log_entries
        except Exception as e:
            self.logger.error(f"[Log Viewer ERROR] Failed to read log file: {e}")
            return []


    def _create_log_content_widget(self, log_entries, popup_width):
        """
        Creates and returns the main content widget for the log popup,
        formatted as a table using GridLayout, with dynamic row heights.
        """
        # Define column widths proportionally for the entire table
        col_timestamp_width = (popup_width - dp(4)) * 0.28 
        col_text_width      = (popup_width - dp(4)) * 0.42 
        col_scores_width    = (popup_width - dp(4)) * 0.30 

        # Main GridLayout for the table (headers + rows)
        table_layout = GridLayout(cols=1, spacing=dp(2), size_hint_y=None, width=popup_width)
        table_layout.bind(minimum_height=table_layout.setter('height'))

        # --- Table Headers ---
        header_row_layout = GridLayout(cols=3, spacing=dp(2), size_hint_y=None, height=dp(40)) 
        header_bg_color = (0.3, 0.3, 0.3, 1) # Darker background for headers

        headers = [
            ("Timestamp", col_timestamp_width), 
            ("Text", col_text_width), 
            ("Scores", col_scores_width)
        ]
        self.header_separator_rects = {} 

        for idx, (header_text, col_width) in enumerate(headers):
            header_label = Label(
                text=f"[b]{header_text}[/b]",
                halign='center', valign='middle', markup=True,
                size_hint_x=None, width=col_width,
                size_hint_y=1, 
                color=(0.9, 0.9, 0.9, 1),
                text_size=(col_width - dp(10), None), 
                padding=[dp(5), dp(5)]
            )
            with header_label.canvas.before:
                Color(*header_bg_color)
                Rectangle(pos=header_label.pos, size=header_label.size)
            
            if idx < len(headers) - 1: 
                with header_label.canvas.after:
                    Color(0.1, 0.1, 0.1, 1) 
                    sep_rect = Rectangle(pos=(header_label.right - dp(1), header_label.y), size=(dp(1), header_label.height))
                    self.header_separator_rects[header_label] = sep_rect
                header_label.bind(pos=lambda instance, value, rect=sep_rect: setattr(rect, 'pos', (instance.right - dp(1), instance.y)),
                                  size=lambda instance, value, rect=sep_rect: setattr(rect, 'size', (dp(1), instance.height)))

            header_row_layout.add_widget(header_label)
        table_layout.add_widget(header_row_layout) 

        # --- Log Entries ---
        if not log_entries:
            no_log_container = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(2))
            no_log_label = Label(text="No log entries found.", 
                                 halign='center', valign='middle',
                                 color=(0.7, 0.7, 0.7, 1),
                                 text_size=(popup_width - dp(10), None), 
                                 padding=[dp(5), dp(5)])
            with no_log_label.canvas.before:
                Color(0, 0, 0, 1) 
                Rectangle(pos=no_log_label.pos, size=no_log_label.size)
            no_log_container.add_widget(no_log_label)
            table_layout.add_widget(no_log_container)

        else:
            self.cell_rects = {} # Re-initialize for each popup instance. This clears old references.

            row_colors = [(0, 0, 0, 1), (0.2, 0.2, 0.2, 1)] 

            for i, entry in enumerate(reversed(log_entries)): 
                row_bg_color = row_colors[0] if i % 2 == 0 else row_colors[1]

                row_container = BoxLayout(orientation='horizontal', size_hint_y=None, spacing=dp(2))
                row_container.bind(minimum_height=row_container.setter('height')) 

                current_row_labels = [] 

                original_timestamp = entry.get('timestamp', 'N/A')
                formatted_timestamp = original_timestamp
                try:
                    dt_object = datetime.datetime.strptime(original_timestamp, "%Y-%m-%d %H:%M:%S")
                    formatted_timestamp = dt_object.strftime("%m %d %H %M")
                except ValueError:
                    pass 


                data_fields = [
                    formatted_timestamp, 
                    entry.get('text', 'N/A'),
                    entry.get('top_scores', 'N/A')
                ]
                column_widths_data = [col_timestamp_width, col_text_width, col_scores_width]

                for j, data in enumerate(data_fields):
                    cell_label = Label(
                        text=str(data),
                        halign='left', valign='top', markup=True,
                        size_hint_x=None, width=column_widths_data[j],
                        size_hint_y=1, 
                        color=(0.9, 0.9, 0.9, 1),
                        text_size=(column_widths_data[j] - dp(10), None), 
                        padding=[dp(5), dp(5)]
                    )
                    cell_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1] + dp(10)))

                    with cell_label.canvas.before:
                        Color(*row_bg_color)
                        rect = Rectangle(pos=cell_label.pos, size=cell_label.size)
                        self.cell_rects[cell_label] = {'bg': rect} 

                    if j < len(data_fields) - 1: 
                        with cell_label.canvas.after:
                            Color(0.1, 0.1, 0.1, 1) 
                            sep_rect = Rectangle(pos=(cell_label.right - dp(1), cell_label.y), size=(dp(1), cell_label.height))
                            self.cell_rects[cell_label]['sep'] = sep_rect 

                    cell_label.bind(pos=self.update_rect_pos, size=self.update_rect_size)
                    
                    row_container.add_widget(cell_label)
                    current_row_labels.append(cell_label) 
                
                if current_row_labels:
                    max_height = max(label.height for label in current_row_labels)
                    row_container.height = max_height
                else:
                    row_container.height = dp(50) 

                table_layout.add_widget(row_container) 
        
        scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=dp(10))
        scroll_view.add_widget(table_layout)
        
        return scroll_view


    def update_rect_pos(self, instance, value):
        """Updates the position of the background rectangle and separator for a cell."""
        if instance in self.cell_rects:
            self.cell_rects[instance]['bg'].pos = value
            if 'sep' in self.cell_rects[instance]:
                self.cell_rects[instance]['sep'].pos = (instance.right - dp(1), instance.y)


    def update_rect_size(self, instance, value):
        """Updates the size of the background rectangle and separator for a cell."""
        if instance in self.cell_rects:
            self.cell_rects[instance]['bg'].size = value
            if 'sep' in self.cell_rects[instance]:
                self.cell_rects[instance]['sep'].size = (dp(1), instance.height)


    def show_log_window(self, button_instance):
        """
        Opens a floating window (Popup) to display log entries.
        Args:
            button_instance: The Kivy Button widget that triggered this window.
        """
        self.logger.info(f"show_log_window called.")

        # Calculate popup size
        popup_width = max(dp(300), Window.width * 0.9) 
        popup_height = max(dp(250), Window.height * 0.8) 
        
        log_entries = self.read_log_file()
        new_content_widget = self._create_log_content_widget(log_entries, popup_width)

        if self.log_popup_instance:
            self.log_popup_instance.content = new_content_widget
            self.log_popup_instance.size = (popup_width, popup_height)
            self.logger.info(f"Existing Log windoaw updated. Size: {self.log_popup_instance.size}, Pos: {self.log_popup_instance.pos}")
        else:
            self.log_popup_instance = Popup(
                title='Hate Speech Detection Logs',
                content=new_content_widget,
                size_hint=(None, None), 
                size=(popup_width, popup_height),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}, 
                auto_dismiss=True,
                separator_height=dp(2), 
                separator_color=(0.1, 0.1, 0.1, 1), 
                background_color=(0.18, 0.18, 0.18, 1) 
            )

        self.log_popup_instance.open()
        self.logger.info(f"Log window opened. Size: {self.log_popup_instance.size}, Pos: {self.log_popup_instance.pos}")


if __name__ == "__main__":
    SpeechRegulatorApp().run()
