import numpy as np

class MorseDecoder:
    def __init__(self, sr=12000, threshold=0.15):
        self.sr = sr
        self.threshold = threshold
        self.buf = np.array([], dtype=np.float32)
        self.last_state = 0
        self.dot_len = 0.08
        self.text = ""

    def process(self, samples):
        self.buf = np.concatenate([self.buf, samples])
        max_len = int(2 * self.sr)
        if len(self.buf) > max_len:
            self.buf = self.buf[-max_len:]
        env = np.abs(self.buf)
        win = int(0.01 * self.sr)
        if len(env) > win:
            env = np.convolve(env, np.ones(win)/win, mode="same")
        binary = (env > self.threshold).astype(int)
        return self.text
