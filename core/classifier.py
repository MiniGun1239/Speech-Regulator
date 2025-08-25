import os
import json
import logging

import numpy as np
from onnxruntime import InferenceSession
from transformers import AutoTokenizer

class HateSpeechClassifier:
    """
    Classifies text as hate speech using an ONNX-optimized Hugging Face model.
    It loads a pre-trained tokenizer, model, and configuration.
    """
    def __init__(self, model_dir="models/minuva", threshold=0.5, resource_path_func=None): # Removed app_logger
        """
        Initializes the classifier by loading the model, tokenizer, and config.
        Args:
            model_dir (str): Relative path to the directory containing the ONNX model,
                             tokenizer.json, and config.json.
            threshold (float): The probability threshold above which a text is considered hate speech.
            resource_path_func (callable): A function to resolve paths for bundled resources.
        """
        self.logger = logging.getLogger("SpeechRegulator") # Use the globally configured logger
        self.resource_path_func = resource_path_func if resource_path_func else (lambda x: x) # Use provided func or identity

        self.model_path = self.resource_path_func(os.path.join(model_dir, "model_optimized_quantized.onnx"))
        self.tokenizer_path = self.resource_path_func(os.path.join(model_dir, "tokenizer.json"))
        self.config_path = self.resource_path_func(os.path.join(model_dir, "config.json"))
        self.threshold = threshold

        self.tokenizer = None
        self.model = None
        self.labels = [] # Will be loaded from config

        self._load_resources()

    def _load_resources(self):
        """Loads the ONNX model, tokenizer, and labels from the config."""
        # --- Load Model ---
        self.logger.debug(f"[Classifier Debug] Attempting to load model from: {self.model_path}")
        if not os.path.exists(self.model_path):
            self.logger.error(f"[Classifier ERROR] Model file not found: {self.model_path}")
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        try:
            self.model = InferenceSession(self.model_path)
        except Exception as e:
            self.logger.error(f"[Classifier ERROR] Failed to load ONNX model from {self.model_path}: {e}")
            raise

        # --- Load Tokenizer ---
        self.logger.debug(f"[Classifier Debug] Attempting to load tokenizer from: {self.tokenizer_path}")
        if not os.path.exists(self.tokenizer_path):
            self.logger.error(f"[Classifier ERROR] Tokenizer file not found: {self.tokenizer_path}")
            raise FileNotFoundError(f"Tokenizer file not found: {self.tokenizer_path}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(os.path.dirname(self.tokenizer_path))
        except Exception as e:
            self.logger.error(f"[Classifier ERROR] Failed to load tokenizer from {os.path.dirname(self.tokenizer_path)}: {e}")
            raise

        # --- Load Config for Labels ---
        self.logger.debug(f"[Classifier Debug] Attempting to load config from: {self.config_path}")
        if not os.path.exists(self.config_path):
            self.logger.warning(f"[Classifier WARNING] Config file not found: {self.config_path}. Labels might be missing.")
            # We can proceed without config, but labels will be numeric indices.
        else:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "id2label" in config:
                        # Convert id2label dictionary (where keys are strings) to a sorted list of labels
                        self.labels = [config["id2label"][str(i)] for i in range(len(config["id2label"]))]
                    else:
                        self.logger.warning(f"[Classifier WARNING] 'id2label' not found in config: {self.config_path}. Labels will be default.")
            except Exception as e:
                self.logger.error(f"[Classifier ERROR] Failed to load or parse config from {self.config_path}: {e}")
        
        self.logger.info(f"[Classifier] Successfully loaded ONNX model with labels: {self.labels if self.labels else 'Not available'}")

    def predict(self, text: str) -> dict:
        """
        Predicts the hate speech scores for a given text.
        Args:
            text (str): The input text to classify.
        Returns:
            dict: A dictionary of {label: score} pairs.
        """
        if not self.tokenizer or not self.model:
            self.logger.error("[Classifier ERROR] Model or tokenizer not loaded. Cannot make predictions.")
            return {}

        inputs = self.tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=512)
        
        # ONNX Runtime expects inputs as a dictionary
        onnx_inputs = {name: inputs[name] for name in inputs.keys()}

        try:
            outputs = self.model.run(None, onnx_inputs)
            # The output of the model is usually a list; take the first element (logits)
            logits = outputs[0]
            
            # Apply sigmoid to convert logits to probabilities
            scores = 1 / (1 + np.exp(-logits))
            
            # Map scores to labels
            result = {}
            for i, score in enumerate(scores[0]): # scores[0] because batch size is 1
                label = self.labels[i] if i < len(self.labels) else f"label_{i}"
                result[label] = float(score) # Convert numpy float to Python float
            return result
        except Exception as e:
            self.logger.error(f"[Classifier ERROR] Error during prediction for text '{text}': {e}")
            return {}

    def is_hate_speech_from_scores(self, scores: dict) -> bool:
        """
        Determines if any score exceeds the defined hate speech threshold.
        Args:
            scores (dict): A dictionary of {label: score} pairs from `predict`.
        Returns:
            bool: True if any score is above the threshold, False otherwise.
        """
        if not scores:
            return False # No scores, so not hate speech

        for label, score in scores.items():
            if score >= self.threshold:
                self.logger.info(f"[Classifier] Hate speech detected: Label '{label}' score {score:.2f} >= threshold {self.threshold}")
                return True
        self.logger.info(f"[Classifier] No hate speech detected for scores: {scores}")
        return False
        
