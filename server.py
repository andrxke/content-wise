import os
import shutil
import tempfile
import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

@app.on_event("startup")
async def startup_event():
    global model
    logger.info(f"Loading TribeModel ({MODEL_ID}) on {DEVICE}...")
    
    # Hybrid optimization: 
    # Use MPS (Mac GPU) for everything else to keep it fast,
    # but strictly use CPU for the audio extractor to prevent crashes.
    config_update = {
        "data.text_feature.device": "accelerate" if DEVICE == "cpu" else DEVICE,
        "data.audio_feature.device": "cpu", # Explicit CPU override
        "data.video_feature.image.device": "accelerate" if DEVICE == "cpu" else DEVICE,
        "data.image_feature.image.device": "accelerate" if DEVICE == "cpu" else DEVICE,
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

@app.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    if not file.filename.endswith((".webm", ".mp4")):
        raise HTTPException(status_code=400, detail="Only .webm or .mp4 files are supported.")
    
    # Save the upload to a temporary file
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=CACHE_DIR) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        logger.info(f"Analyzing video: {tmp_path}")
        
        # 1. Build events dataframe
        events = model.get_events_dataframe(video_path=tmp_path)
        
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
        # Cleanup the temporary video file
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup temp file {tmp_path}: {cleanup_error}")
