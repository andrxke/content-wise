document.addEventListener('DOMContentLoaded', () => {
  const capBtn = document.getElementById('capture-btn');
  const statusCard = document.getElementById('status-card');
  const statusIcon = document.getElementById('status-icon');
  const focusStateTitle = document.getElementById('focus-state-title');
  const confidenceText = document.getElementById('confidence-text');

  const barFocus = document.getElementById('bar-focus');
  const barLured = document.getElementById('bar-lured');
  const barDistracted = document.getElementById('bar-distracted');
  const topRegionsList = document.getElementById('top-regions-list');
  const intervalSelect = document.getElementById('interval-select');

  // Load latest state and settings
  chrome.storage.local.get(['latest', 'captureInterval'], (data) => {
    if (data.latest) {
      updateUI(data.latest);
    }
    if (data.captureInterval) {
      intervalSelect.value = data.captureInterval;
    } else {
      intervalSelect.value = 'manual';
    }
  });

  // Handle setting change
  intervalSelect.addEventListener('change', (e) => {
    chrome.storage.local.set({ captureInterval: e.target.value });
  });

  // Manual Capture
  let isCapturing = false;
  capBtn.addEventListener('click', async () => {
    if (isCapturing) return;
    isCapturing = true;
    capBtn.disabled = true;

    capBtn.textContent = '● CHECKING...';
    capBtn.style.opacity = '0.5';

    try {
      // 1. Check if server is running
      const res = await fetch('http://127.0.0.1:8000/health');
      if (!res.ok) throw new Error("Server returned non-200");

      // 2. Trigger recording if online
      capBtn.textContent = '● RECORDING...';
      chrome.runtime.sendMessage({ type: "MANUAL_TRIGGER" }, () => {
        setTimeout(() => {
          isCapturing = false;
          capBtn.disabled = false;
          window.close(); // Close popup so background script can do its thing
        }, 500);
      });

    } catch (err) {
      // Server is offline
      capBtn.textContent = 'SERVER OFFLINE';
      capBtn.style.opacity = '1';
      capBtn.style.backgroundColor = '#808080';

      // Reset button after 3 seconds
      setTimeout(() => {
        capBtn.textContent = '● REC';
        capBtn.style.backgroundColor = '#ff3333';
        isCapturing = false;
        capBtn.disabled = false;
      }, 3000);
    }
  });

  function updateUI(result) {
    const s = result.focus_state;

    // Update card styling
    statusCard.className = 'status-card ' + s;

    // Update text
    focusStateTitle.textContent = s;
    confidenceText.textContent = `Confidence: ${(result.confidence * 100).toFixed(1)}%`;

    // Update icon
    if (s === 'focused') statusIcon.textContent = '✓';
    else if (s === 'lured') statusIcon.textContent = '!';
    else statusIcon.textContent = '○';

    // Update bars
    // Values might be negative if completely unactivated, clamp manually for viz
    const clamp = (v) => Math.max(0, Math.min(100, v * 100));

    barFocus.style.width = clamp(result.scores.focused) + '%';
    barLured.style.width = clamp(result.scores.lured) + '%';
    barDistracted.style.width = clamp(result.scores.distracted) + '%';

    // Update regions
    if (result.top_active_regions && result.top_active_regions.length > 0) {
      topRegionsList.textContent = result.top_active_regions.join(', ');
    }
  }
});
