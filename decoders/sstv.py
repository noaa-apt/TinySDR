import wave
import numpy as np
import time

class SSTVRecorder:
    def __init__(self, sr=12000):
        self.sr = sr
        self.recording = False
        self.frames = []

    def start(self):
        self.recording = True
        self.frames = []

    def feed(self, samples):
        if self.recording:
            self.frames.append((samples * 32767).astype(np.int16))

    def stop_and_save(self, filename=None):
        self.recording = False
        if not self.frames:
            return None
        if filename is None:
            filename = f"sstv_{int(time.time())}.wav"
        data = np.concatenate(self.frames)
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sr)
            wf.writeframes(data.tobytes())
        return filename
