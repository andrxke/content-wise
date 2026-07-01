import os
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pandas as pd
from neuralset.events.utils import standardize_events

from tribev2.demo_utils import TribeModel
from interpreter import interpret_brain_activity
from config import CACHE_DIR, DEVICE, MODEL_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ContentWise Inference Server")

# Allow requests from the Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to chrome-extension://<id>
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model variable
model = None

# ── Video preprocessing settings ──
# Downsample captured video before feeding to the model.
# The visual feature extractors (DINOv2, VJEPA2) resize frames internally
# anyway, so sending 1080p is pure waste.
DOWNSAMPLE_RESOLUTION = 360   # height in pixels (-2:360 keeps aspect ratio)
DOWNSAMPLE_FPS = 1            # 1fps — minimal frame count for speed

@app.on_event("startup")
async def startup_event():
    global model
    logger.info(f"Loading TribeModel ({MODEL_ID}) on {DEVICE}...")
    
    # Visual-only pipeline: only use the video extractor.
    # Audio and text features are not needed — the model handles missing
    # modalities by zero-filling those feature dimensions.
    # Note: neuralset extractors only accept auto/cpu/cuda/accelerate —
    # not 'mps'. Using 'auto' falls back to CPU for feature extraction.
    # The TribeModel prediction head itself runs on MPS (set via DEVICE).
    config_update = {
        "data.video_feature.image.device": "auto",
        "data.image_feature.image.device": "auto",
    }
    
    model = TribeModel.from_pretrained(
        MODEL_ID, 
        cache_folder=str(CACHE_DIR), 
        device=DEVICE,
        config_update=config_update
    )
    logger.info("TribeModel loaded.")

@app.get("/health")
def health_check():
    return {"status": "ok", "device": DEVICE, "model_loaded": model is not None}


def downsample_video(input_path: str, output_path: str) -> str:
    """Downsample a video to low resolution and frame rate using ffmpeg.
    
    Returns the path to the downsampled file, or the original if ffmpeg fails.
    """
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"scale=-2:{DOWNSAMPLE_RESOLUTION},fps={DOWNSAMPLE_FPS}",
            "-an",              # strip audio track entirely
            "-c:v", "libx264",  # re-encode as h264 for broad compatibility
            "-preset", "ultrafast",
            "-crf", "28",       # lower quality is fine — features are extracted at low res
            output_path,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and os.path.getsize(output_path) > 0:
            logger.info(
                "Downsampled video: %s → %s (%.1f KB → %.1f KB)",
                input_path, output_path,
                os.path.getsize(input_path) / 1024,
                os.path.getsize(output_path) / 1024,
            )
            return output_path
        else:
            logger.warning("ffmpeg downsample failed, using original: %s", result.stderr[:200])
            return input_path
    except Exception as e:
        logger.warning("ffmpeg not available or failed (%s), using original video", e)
        return input_path


def build_video_only_events(video_path: str) -> pd.DataFrame:
    """Build a minimal events DataFrame with only a Video event.
    
    By only including Video events (no Audio/Word events), the TribeV2
    data loader will automatically skip the text and audio feature
    extractors, eliminating WhisperX, Llama-3.2-3B, and Wav2VecBert
    from the pipeline entirely.
    """
    events = pd.DataFrame([{
        "type": "Video",
        "filepath": video_path,
        "start": 0,
        "timeline": "default",
        "subject": "default",
    }])
    return standardize_events(events)


@app.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    if not file.filename.endswith((".webm", ".mp4")):
        raise HTTPException(status_code=400, detail="Only .webm or .mp4 files are supported.")
    
    # Save the upload to a temporary file
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=CACHE_DIR) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    ds_path = None
    try:
        logger.info(f"Analyzing video: {tmp_path}")
        
        # 0. Downsample to 360p @ 2fps — dramatically reduces frame count
        ds_path = tmp_path.replace(suffix, "_ds.mp4")
        video_to_process = downsample_video(tmp_path, ds_path)
        
        # 1. Build video-only events (no audio/text extraction)
        events = build_video_only_events(video_to_process)
        
        # 2. Run prediction
        # predict returns (preds, segments)
        preds, segments = model.predict(events, verbose=False)
        
        if len(preds) == 0:
            raise ValueError("Model prediction returned no segments (possibly empty video or no events).")

        # 3. Aggregate across time segments (mean across time)
        mean_pred = preds.mean(axis=0)

        # 4. Interpret brain activity
        result = interpret_brain_activity(mean_pred)

        return result

    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup temporary files
        for path in [tmp_path, ds_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file {path}: {cleanup_error}")
