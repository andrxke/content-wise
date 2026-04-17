let recorder;
let data = [];

chrome.runtime.onMessage.addListener(async (message) => {
  if (message.target !== 'offscreen') return;

  if (message.type === 'START_RECORDING') {
    startRecording(message.data.streamId, message.data.durationMs);
  } else if (message.type === 'STOP_RECORDING') {
    stopRecording();
  }
});

async function startRecording(streamId, durationMs) {
  if (recorder?.state === 'recording') {
    throw new Error('Called startRecording while recording is in progress.');
  }

  const mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: {
        chromeMediaSource: 'tab',
        chromeMediaSourceId: streamId
      }
    },
    video: {
      mandatory: {
        chromeMediaSource: 'tab',
        chromeMediaSourceId: streamId
      }
    }
  });

  // Record as WebM
  recorder = new MediaRecorder(mediaStream, { mimeType: 'video/webm' });
  
  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      data.push(event.data);
    }
  };

  recorder.onstop = () => {
    mediaStream.getTracks().forEach((t) => t.stop());
    const blob = new Blob(data, { type: 'video/webm' });
    
    // Read the blob into a data URL so we can pass it back to the service worker
    const reader = new FileReader();
    reader.onloadend = () => {
      chrome.runtime.sendMessage({
        type: 'RECORDING_COMPLETE',
        dataUrl: reader.result
      });
      // Clear data for next recording
      data = [];
    };
    reader.readAsDataURL(blob);
  };

  recorder.start();

  // Stop recording automatically after durationMs
  setTimeout(() => {
    if (recorder.state === 'recording') {
      stopRecording();
    }
  }, durationMs);
}

function stopRecording() {
  if (recorder?.state === 'recording') {
    recorder.stop();
  }
}
