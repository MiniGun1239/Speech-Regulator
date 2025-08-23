# Speech-Regulator

**Real-time hate speech detection for public and classroom environments, built with Python + Kivy.**

Speech-Regulator is a cross-platform application designed to detect and discourage hate speech in real-world settings. It leverages speech-to-text processing and machine learning classification to identify harmful language and respond with visual or auditory cues. The system is built with ethical considerations in mind—prioritizing privacy, transparency, and offline capability.

---

## Platforms Supported

- **Android** (via Buildozer)
- **Windows** (via PyInstaller)

---

## Features

- **Live Audio Capture**: Uses device microphone to monitor speech in real time  
- **Speech-to-Text Engine**: Converts spoken language to text using offline or online STT modules  
- **Hate Speech Detection**: Classifies transcribed text using a lightweight ONNX model  
- **Responsive Feedback**: Triggers visual or auditory alerts to discourage harmful speech  
- **Privacy-First Design**: No cloud logging or external data transmission by default  
- **Event Logging**: Optionally stores detection events for review and analysis  

---

## Project Structure

Speech-Regulator/  
├── main.py                                     # Kivy app entry point  
├── ui/                                         # Kivy layout files (.kv)  
├── core/  
│   ├── stt_engine.py                           # Speech-to-text logic  
│   ├── classifier.py                           # Hate speech detection  
│   └── response_handler.py                     # Feedback and logging  
├── models/  
│   └── minuva/
|       ├──config.json
|       ├──model_optimized_quantisized.onnx     # Your model
|       └──tokenizer.json
├── logs/
|   └──
├── android/  
│   └── buildozer.spec                          # Android build config  
├── windows/  
│   └── main.spec                               # Windows build config  
├── assets/  
│   └── icons, sounds, etc.  
├── README.md  
└── requirements.txt  

---
## Getting Started

### Windows Build (PyInstaller)
| In Speech-Regulator/windows
```bash
pip install -r requirements.txt
pyinstaller pyinstaller.spec
```
### Android Build (Buildozer) (WSL or Linux required)

```bash
sudo apt install buildozer
buildozer init
buildozer -v android debug
```
| Make sure to enable microphone permissions in [buildozer.spec].

### Model Details

- **Format:** ONNX
- **Input:** Transcribed text
- **Output:** Binary classification (Hate / Neutral)
- **Optional/Later:** Confidence score thresholding for nuanced feedback

---

### Ethical Considerations

**Speech-Regulator is designed with the following principles:**

- **Transparency:** Users are informed when detection occurs
- **Privacy:** No audio or text is stored or transmitted externally by default
- **Context Awareness:** Future versions may include contextual filtering to reduce false positives

---

### Screenshots & Demo

*Coming soon*

---

### Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you’d like to modify.

---

### License

This project is licensed under the MIT License.

---

### Author

github.com/MiniGun1239

---
