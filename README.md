# Real-Time Hate Speech Detection System

A classroom-oriented system designed to detect and respond to hate speech in real-time. This project features a Raspberry Pi for audio collection and a powerful PC backend for transcription, classification, and responsive signaling.

---

## System Architecture

| Component        | Role                                              |
|------------------|---------------------------------------------------|
| Raspberry Pi     | Records short audio clips, sends to PC            |
| Laptop (R5-5500U)| Handles all signal processing and classification  |
| LEDs / Sensors   | Provides classroom-friendly feedback mechanisms   |

---

## Key Features

- **Noise Suppression**: Optional pre-processing with RNNoise (native binary for speed)
- **Speech Detection**: Silero VAD filters non-speech chunks
- **Speech Recognition**: Whisper (tiny.en or base.en for <6s inference)
- **Custom Hate Speech Boundaries**:
  - Tiered keyword scoring
  - Optional ML classifier using ONNX or scikit-learn
- **Detection Sensitivity**:
  - Threshold-based response levels
  - LED alerts for mild/serious detection
- **Privacy Controls**:
  - Only two most recent clips stored
- **Reliability**: Full processing must stay under clip length minus 1s

---

## Performance Goals

| Clip Length | Max Processing Time | Achievable Components                        |
|-------------|---------------------|----------------------------------------------|
| 5s          | ≤ 4s                | Silero + RNNoise + tiny.en + Rule Classifier |
| 10s         | ≤ 9s                | RNNoise + base.en + ONNX CNN model           |

*Tested on R5-5500U laptop with Vega 7 iGPU and 20GB RAM*

---

## Demo Mode

Even though the Pi only records, its presence elevates presentation value. Add-ons for demo setup:
- LEDs: blink, fade, or flash based on severity score
- LCD display: show real-time response messages
- Touch input: reset state or manually flag speech

---

## Future Plans
    Add teacher dashboard for live incident review
    Include multi-language hate speech detection
    Add anonymized reporting for flagged clips
    Replace keyword matching with phoneme-based detection for raw audio processing

## Ethical Principles
This project prioritizes:
    Privacy over surveillance
    Transparency over hidden monitoring
    Intent-aware classification for context-sensitive detection

Hate speech detection should Promote safer spaces, not punish random interactions. This system emphasizes silent flags and gradual escalation.

##  How to Run

```bash
# Record audio on Pi (chunked)
arecord -D plughw:1,0 -f cd -t wav -d 5 -r 16000 -c 1 clip.wav

# Transfer to PC
scp clip.wav username@pc_ip:~/audio_clips/

# On PC: Process the clip
python process.py clip.wav
```
---
