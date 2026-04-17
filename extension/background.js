const SERVER_URL = "http://127.0.0.1:8000/analyze";
const RECORDING_DURATION_MS = 10000; // 10 seconds

let isRecording = false;

function updateAlarm(interval) {
  if (interval === 'manual' || !interval) {
    chrome.alarms.clear("periodic-capture");
    console.log("Cleared periodic alarms. Manual mode only.");
  } else {
    const mins = parseInt(interval, 10);
    chrome.alarms.create("periodic-capture", { periodInMinutes: mins });
    console.log(`Set periodic capture to every ${mins} minutes.`);
  }
}

// Initialize on install
chrome.runtime.onInstalled.addListener(() => {
  console.log("ContentWise installed. Defaulting to manual mode.");
  chrome.storage.local.set({ captureInterval: 'manual' });
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.captureInterval) {
    updateAlarm(changes.captureInterval.newValue);
  }
});

// Sync on startup 
chrome.storage.local.get({ captureInterval: 'manual' }, (data) => {
  updateAlarm(data.captureInterval);
});

// Periodic alarm listener
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "periodic-capture") {
    if (isRecording) {
      console.log("Already recording, skipping this cycle.");
      return;
    }
    await triggerCapture();
  }
});

// Create offscreen document if it doesn't exist
async function ensureOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({});
  const offscreenDocument = existingContexts.find(
    (c) => c.contextType === 'OFFSCREEN_DOCUMENT'
  );

  if (!offscreenDocument) {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['USER_MEDIA'],
      justification: 'Recording from chrome.tabCapture API'
    });
  }
}

// Ensure the popup can manually trigger a capture
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "MANUAL_TRIGGER") {
    triggerCapture().then(() => sendResponse({ status: "started" }));
    return true;
  }
  if (message.type === "RECORDING_COMPLETE") {
    // The offscreen document sends this
    handleRecordingComplete(message.dataUrl);
    isRecording = false;
  }
});

// Start the capture process
async function triggerCapture() {
  console.log("Triggering capture...");
  isRecording = true;
  chrome.action.setBadgeText({ text: "REC" });
  chrome.action.setBadgeBackgroundColor({ color: "#FF0000" });

  try {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!activeTab || activeTab.url.startsWith("chrome://")) {
      console.log("No active recording target allowed. Aborting silently.");
      isRecording = false;
      return;
    }

    // This may prompt the user if they haven't granted tabCapture yet
    // Note: tabCapture requires the user to click the extension icon at least once to grant activeTab privileges,
    // unless you use desktopCapture. However, activeTab + periodic alarm might fail if activeTab expires.
    // In Manifest V3, tabCapture.getMediaStreamId can be used to get a stream ID without a prompt IF we are currently active.

    chrome.tabCapture.getMediaStreamId({ targetTabId: activeTab.id }, async (streamId) => {
      if (chrome.runtime.lastError || !streamId) {
        console.error("Failed to get MediaStreamId: ", chrome.runtime.lastError);
        isRecording = false;
        chrome.action.setBadgeText({ text: "ERR" });
        return;
      }

      await ensureOffscreenDocument();

      // Tell offscreen to start recording
      chrome.runtime.sendMessage({
        type: 'START_RECORDING',
        target: 'offscreen',
        data: {
          streamId: streamId,
          durationMs: RECORDING_DURATION_MS
        }
      });
    });
  } catch (err) {
    console.error("Capture error:", err);
    isRecording = false;
    chrome.action.setBadgeText({ text: "ERR" });
  }
}

async function handleRecordingComplete(dataUrl) {
  chrome.action.setBadgeText({ text: "PROC" });
  chrome.action.setBadgeBackgroundColor({ color: "#FFA500" });
  console.log("Recording complete. Sending to server...");

  try {
    // Convert dataUrl to a Blob to send as file
    const response = await fetch(dataUrl);
    const blob = await response.blob();

    // Check blob size
    if (blob.size < 1000) {
      console.error("Captured blob is suspiciously small. Aborting.");
      chrome.action.setBadgeText({ text: "ERR" });
      return;
    }

    const formData = new FormData();
    formData.append("file", blob, "capture.webm");

    const analysisRes = await fetch(SERVER_URL, {
      method: "POST",
      body: formData
    });

    if (!analysisRes.ok) {
      throw new Error("Server returned " + analysisRes.status);
    }

    const analysisResult = await analysisRes.json();
    console.log("Received result:", analysisResult);

    // Update Chrome Storage
    const timestamp = Date.now();
    chrome.storage.local.get({ history: [] }, (data) => {
      const history = data.history;
      history.unshift({ timestamp, result: analysisResult });
      if (history.length > 50) history.pop();
      chrome.storage.local.set({ history, latest: analysisResult });
    });

    // Update Badge
    const focusState = analysisResult.focus_state;
    if (focusState === "focused") {
      chrome.action.setBadgeText({ text: "✓" });
      chrome.action.setBadgeBackgroundColor({ color: "#00FF00" });
    } else if (focusState === "lured") {
      chrome.action.setBadgeText({ text: "!" });
      chrome.action.setBadgeBackgroundColor({ color: "#FFA500" });
    } else {
      chrome.action.setBadgeText({ text: "O" });
      chrome.action.setBadgeBackgroundColor({ color: "#808080" });
    }

  } catch (err) {
    console.error("Analysis error:", err);
    chrome.action.setBadgeText({ text: "ERR" });
    chrome.action.setBadgeBackgroundColor({ color: "#FF0000" });
  }
}
