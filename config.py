import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.resolve()
CACHE_DIR = ROOT_DIR / "cache"

# TribeV2 settings
MODEL_ID = "facebook/tribev2"
DEVICE = "cpu" # Switched to CPU because the Transformers audio extractor fails on MPS

# Ensure directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
