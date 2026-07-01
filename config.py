import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.resolve()
CACHE_DIR = ROOT_DIR / "cache"

# TribeV2 settings
MODEL_ID = "facebook/tribev2"
DEVICE = "mps"  # Apple Silicon GPU — audio extractor is pinned to CPU in server.py

# Ensure directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
