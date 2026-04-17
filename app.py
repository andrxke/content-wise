import uvicorn
import argparse
import logging
from config import DEVICE, CACHE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_server(host="127.0.0.1", port=8000, use_cpu=False):
    """
    Start the FastAPI server programmatically.
    This makes it easier to bundle into a desktop app later.
    """
    import os
    if use_cpu:
        os.environ["USE_CPU"] = "1"
    
    logger.info(f"Starting ContentWise server on {host}:{port}")
    logger.info(f"Cache dir: {CACHE_DIR}")
    
    # We use uvicorn.run to start the app. 
    # Passing "server:app" as a string allows uvicorn to handle autoreload if needed.
    uvicorn.run("server:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContentWise Local Backend Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--cpu", action="store_true", help="Force CPU inference (disable MPS)")
    
    args = parser.parse_args()
    
    start_server(host=args.host, port=args.port, use_cpu=args.cpu)
