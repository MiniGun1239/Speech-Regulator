# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

# Set up paths relative to the spec file
# This assumes your main.py, ui/ and models/ directories are siblings to main.spec
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir) # Add current directory to Python path for analysis

block_cipher = None

# --- COLLECTING KIVY FILES ---
# Kivy often needs its data files. collect_data_files is the best way.
kivy_data = collect_data_files('kivy')

# --- COLLECTING ML LIBRARY FILES (CRITICAL!) ---
# These libraries are complex and often miss native binaries/data.
# collect_dynamic_libs is crucial for native DLLs.
# collect_data_files for Python-level data.
torch_data = collect_data_files('torch')
torch_libs = collect_dynamic_libs('torch') # Collects native Torch DLLs

onnxruntime_data = collect_data_files('onnxruntime')
onnxruntime_libs = collect_dynamic_libs('onnxruntime') # Collects native ONNX Runtime DLLs

# sounddevice depends on PortAudio. This helps collect its native libraries.
sounddevice_libs = collect_dynamic_libs('sounddevice')

# faster_whisper depends on onnxruntime, so if onnxruntime is fixed, it usually works.
# No specific collect for faster_whisper's own data usually needed beyond onnxruntime.

# tokenizers and huggingface_hub are more Python-centric, hiddenimports usually suffices.


a = Analysis(
    ['main.py'],
    pathex=[current_dir], # Ensure the current directory is the primary path
    binaries=torch_libs + onnxruntime_libs + sounddevice_libs, # Include collected native libraries
    datas=[
        # --- Your application's specific data files ---
        (os.path.join(current_dir, 'ui', 'main.kv'), 'ui'),
        (os.path.join(current_dir, 'models', 'minuva', 'model_optimized_quantized.onnx'), 'models/minuva'),
        (os.path.join(current_dir, 'models', 'minuva', 'tokenizer.json'), 'models/minuva'),
        (os.path.join(current_dir, 'models', 'minuva', 'config.json'), 'models/minuva'),
        (os.path.join(current_dir, 'ui', 'assets', 'alert.wav'), 'ui/assets'),
    ] + kivy_data + torch_data + onnxruntime_data, # Add collected data files from libraries
    hiddenimports=[
        # --- Common hidden imports for Kivy and ML libs ---
        'kivy.core.window',
        'kivy.core.audio.sound_sdl2', # If Kivy sound is used implicitly
        'sounddevice._sd', # Explicitly important for sounddevice
        'torch._C', # Often needed for torch
        'torch.cuda', # Even if not using CUDA, PyTorch might check for it
        'onnxruntime.capi',
        'onnxruntime.capi._pybind_state',
        'huggingface_hub.snapshot_download', # Used by faster_whisper
        'faster_whisper.utils', # Can be missed
        # Add any other modules that cause 'ModuleNotFound' at runtime
    ],
    hookspath=[], # PyInstaller has built-in hooks for most of these; custom hooks rarely needed initially
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False, # Set to True for debugging if you want to inspect contents of .exe more easily
)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='SpeechRegulator', # Your desired executable name
          debug=False, # Set to True for detailed console output during execution for debugging
          bootloader_ignore_signals=False,
          strip=False,
          upx=True, # Compresses the executable (can make it slower to start, but smaller)
          console=True, # IMPORTANT: Set to True to get a console window for debugging output
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )

