import sounddevice as sd
import numpy as np
import threading
from collections import deque

class AudioPlayer:
    def __init__(self, sample_rate=12000):
        self.sr = sample_rate
        self.queue = deque(maxlen=20)
        self.gain = 1.0
        self.mute = False
        self.stream = None
        self.lock = threading.Lock()

    def start(self):
        self.stream = sd.OutputStream(
            samplerate=self.sr, channels=1, dtype="float32",
            callback=self._callback, blocksize=1024
        )
        self.stream.start()

    def _callback(self, outdata, frames, time, status):
        with self.lock:
            if self.mute or not self.queue:
                outdata.fill(0)
                return
            data = self.queue.popleft()
            if len(data) < frames:
                data = np.pad(data, (0, frames - len(data)))
            outdata[:, 0] = data[:frames] * self.gain

    def feed(self, samples):
        with self.lock:
            self.queue.append(samples)

    def set_gain(self, g):
        self.gain = max(0.0, min(2.0, g))

    def set_mute(self, m):
        self.mute = m

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
