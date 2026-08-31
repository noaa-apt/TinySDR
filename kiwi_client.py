#!/usr/bin/env python3

import json
import struct
import threading
import time
from websocket import create_connection, WebSocketConnectionClosedException
import numpy as np

class KiwiClient:
    def __init__(self, host, port=8073, password="", user="MiniKiwiRX"):
        self.host = host
        self.port = port
        self.password = password
        self.user = user
        self.ws = None
        self.running = False
        self.sample_rate = 12000
        self.freq = 7100.0
        self.mode = "usb"
        self.low_cut = 300
        self.high_cut = 2700
        self.audio_callback = None
        self._thread = None
        self._seq = 0

    def connect(self):
        ts = int(time.time() * 1000)
        url = f"ws://{self.host}:{self.port}/{ts}/SND"
        self.ws = create_connection(url, timeout=10)
        self._send(f"SET auth t=kiwi p={self.password}")
        self._send(f"SET ident_user={self.user}")
        self._send("SET AR OK in=12000 out=12000")
        self._send("SET squelch=0 max=0")
        self._send("SET genattn=0")
        self._send("SET gen=0 mix=-1")
        self._send("SET compression=0")  
        self.set_mod(self.mode, self.low_cut, self.high_cut, self.freq)
        self._send("SET agc=1 hang=0 thresh=-100 slope=6 decay=1000 manGain=50")
        self.running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def _send(self, msg):
        if self.ws:
            self.ws.send(msg)

    def set_freq(self, freq_khz):
        self.freq = freq_khz
        self.set_mod(self.mode, self.low_cut, self.high_cut, freq_khz)

    def set_mod(self, mod, lc, hc, freq):
        self.mode = mod.lower()
        self.low_cut = lc
        self.high_cut = hc
        self.freq = freq
        self._send(f"SET mod={self.mode} low_cut={lc} high_cut={hc} freq={freq:.3f}")

    def set_passband(self, lc, hc):
        self.set_mod(self.mode, lc, hc, self.freq)

    def _recv_loop(self):
        while self.running:
            try:
                data = self.ws.recv()
                if isinstance(data, bytes) and data[:3] == b"SND":
                    flags = data[3]
                    seq = struct.unpack(">I", data[4:8])[0]
                    smeter = struct.unpack(">h", data[8:10])[0]
                    samples = np.frombuffer(data[10:], dtype="<i2")  
                    if self.audio_callback:
                        self.audio_callback(samples.astype(np.float32) / 32768.0, smeter)
                elif isinstance(data, str) and data.startswith("MSG"):
                    pass
            except (WebSocketConnectionClosedException, Exception):
                break
        self.running = False

    def close(self):
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
