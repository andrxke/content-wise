# ContentWise

ContentWise is a locally-hosted browser extension and backend server designed to monitor user tab content and predict cognitive states (such as Focused, Lured, or Distracted). It leverages an advanced multimodal brain encoding foundation model to analyze what you are watching and listening to, predicting your level of engagement.

To ensure your privacy, the entire pipeline runs locally on your machine.

## Overview

The project consists of two main components:
1. **Chrome Extension**: Captures tab activity locally and sends brief video/audio snippets to the backend server.
2. **Inference Backend Server**: A FastAPI-based Python server that analyzes the media using the [TRIBE v2](https://github.com/facebookresearch/tribev2) model (a foundation model of vision, audition, and language). It predicts simulated fMRI brain responses and maps them onto functional networks to determine your cognitive state.

## Repository Structure

- `extension/` - Chrome extension source code.
- `tribev2/` - Source code for the TRIBE v2 inference model.
- `app.py` / `server.py` - FastAPI backend server wrapping the model.
- `interpreter.py` - Logic for interpreting the simulated brain activity into cognitive states.
- `setup.sh` - Dependency installation script.
- `start.sh` - Backend server execution script.

## Setup & Installation

### 1. Start the Backend Server

Ensure you have Python 3.11+ installed and Conda available on your system. Run the setup script to install all required dependencies (including PyTorch, FastAPI, and TribeV2 dependencies).

```bash
./setup.sh
```

Then, start the server:

```bash
./start.sh
```

The FastAPI inference server will initialize and run locally on `127.0.0.1:8000`. It will automatically download the required `facebook/tribev2` model weights on the first run.

### 2. Install the Chrome Extension

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable "Developer mode" in the top-right corner.
3. Click "Load unpacked" and select the `extension` folder located in this repository.
4. Pin the ContentWise extension to your toolbar to access it quickly.

## How It Works

1. The extension uses Chrome's `tabCapture` API to seamlessly record a brief segment of the active tab.
2. The recording is submitted to the local backend server via the `/analyze` endpoint (no data leaves your machine).
3. The server processes the video and audio using the TRIBE v2 model, mapping the multimodal representation onto a simulated cortical surface to estimate brain region engagement.
4. The `interpreter.py` module evaluates the highest-activating functional networks (e.g., Prefrontal for focus, Ventral attention for visual luring, or the Default Mode network for distraction).
5. The processed cognitive state interpretation is returned back to the extension UI.
