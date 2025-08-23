import os
import json
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

# Define the sigmoid function for converting model outputs to probabilities
SIGMOID = lambda x: 1 / (1 + np.exp(-x))

class HateSpeechClassifier:
    """
    Uses an ONNX toxicity model (in this case: 'minuva/MiniLMv2-toxic-jigsaw-onnx') for efficient hate speech detection.
    Expects model files in: model_dir/{model_optimized_quantized.onnx, tokenizer.json, config.json}.
    Includes a fallback mechanism if the ONNX model cannot be loaded.
    """
    def __init__(self, model_dir="models/minuva", provider="CPUExecutionProvider", threshold=0.5):
        """
        Initializes the HateSpeechClassifier.
        Args:
            model_dir (str): Directory containing the ONNX model, tokenizer, and config files.
            provider (str): ONNX Runtime execution provider (e.g., "CPUExecutionProvider", "CUDAExecutionProvider").
                            "CUDAExecutionProvider" is highly recommended for GPU acceleration.
            threshold (float): Score threshold (0-1) above which text is classified as hate speech.
        """
        self.threshold = threshold
        self.available = False  # Flag to indicate if the ONNX model was successfully loaded
        self.id2label = {}      # Maps numerical label IDs to human-readable labels

        # Construct full paths to model files
        model_path = os.path.join(model_dir, "model_optimized_quantized.onnx")
        tok_path   = os.path.join(model_dir, "tokenizer.json")
        cfg_path   = os.path.join(model_dir, "config.json")

        # Attempt to load the ONNX model and tokenizer
        try:
            # Check if model directory exists before proceeding
            if not os.path.exists(model_dir):
                raise FileNotFoundError(f"Model directory not found: {model_dir}")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"ONNX model file not found: {model_path}")
            if not os.path.exists(tok_path):
                raise FileNotFoundError(f"Tokenizer file not found: {tok_path}")
            if not os.path.exists(cfg_path):
                raise FileNotFoundError(f"Config file not found: {cfg_path}")

            # Initialize ONNX Inference Session
            # It's recommended to use "CUDAExecutionProvider" if a compatible GPU is available
            self.session = ort.InferenceSession(model_path, providers=[provider])
            
            # Load and configure the tokenizer
            self.tokenizer = Tokenizer.from_file(tok_path)
            self.tokenizer.enable_padding()  # Enable padding to max_length for consistent input
            self.tokenizer.enable_truncation(max_length=256) # Truncate sequences longer than 256 tokens

            # Load model configuration (specifically for id2label mapping)
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            
            # Normalize id2label keys to integers as they might be strings in the config file
            self.id2label = {int(k): v for k, v in cfg.get("id2label", {}).items()}
            self.available = True
            print(f"[Classifier] Successfully loaded ONNX model with labels: {list(self.id2label.values())}")

        except Exception as e:
            # Fallback to a simple keyword-based classifier if ONNX model loading fails
            print(f"[Classifier WARNING] ONNX model could not be loaded ({e}). "
                  f"Falling back to a basic keyword rule-based classifier.")
            # A tiny, hardcoded keyword list to keep the application functional
            self.badwords = {"slur", "trash", "hate", "idiot", "stupid", "kill", "harass", "attack", "toxic"}

    def predict(self, text: str) -> dict:
        """
        Predicts toxicity scores for the given text.
        Returns a dictionary mapping label names to their respective scores (0 to 1).
        If the ONNX model is unavailable, it uses a simpler keyword-based fallback.
        Args:
            text (str): The input text to classify.
        Returns:
            dict: A dictionary where keys are toxicity labels (e.g., "toxic", "insult")
                  and values are their corresponding float scores (0-1).
                  Returns an empty dictionary if input text is empty or whitespace.
        """
        if not text or not text.strip():
            return {}

        # Use fallback classifier if ONNX model is not available
        if not self.available:
            lower_text = text.lower()
            # Simple keyword matching: assign high score if any badword is present, else low score
            score = 0.8 if any(word in lower_text for word in self.badwords) else 0.05
            return {"toxic": score}

        # Encode the text using the loaded tokenizer
        enc = self.tokenizer.encode(text)
        
        # Prepare inputs for the ONNX model
        # Input_ids, attention_mask, and token_type_ids are standard for BERT-family models
        inputs = {
            "input_ids":      np.array([enc.ids], dtype=np.int64),
            "attention_mask": np.array([enc.attention_mask], dtype=np.int64),
            "token_type_ids": np.array([enc.type_ids], dtype=np.int64),
        }
        
        # Run inference using the ONNX session
        outputs = self.session.run(None, inputs)[0] # The model returns a single output tensor
        scores = SIGMOID(outputs)[0]                # Apply sigmoid to convert logits to probabilities

        # Map numerical scores back to human-readable labels
        return {self.id2label[i]: float(scores[i]) for i in range(len(scores))}

    def is_hate_speech_from_scores(self, scores: dict) -> bool:
        """
        Determines if the text is classified as hate speech based on the predicted scores
        and the predefined threshold.
        Args:
            scores (dict): Dictionary of label-to-score mappings from the predict method.
        Returns:
            bool: True if any label's score exceeds the threshold, False otherwise.
        """
        if not scores:
            return False
        # Check if any of the predicted scores meet or exceed the classification threshold
        return any(v >= self.threshold for v in scores.values())

