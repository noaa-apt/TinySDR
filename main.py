#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from kiwi_client import KiwiClient
from audio_player import AudioPlayer
from decoders.morse import MorseDecoder
from decoders.sstv import SSTVRecorder
from decoders.wefax import WeFAXRecorder  # copy of SSTVRecorder renamed

class MiniKiwiGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MiniKiwiRX")
        self.geometry("720x180")
        self.resizable(False, False)
        self.configure(bg="#c0c0c0")

        self.client = None
        self.player = AudioPlayer()
        self.morse = MorseDecoder()
        self.sstv = SSTVRecorder()
        self.wefax = WeFAXRecorder()
        self.freq = 7100.00
        self.mode = "usb"
        self.filter_bw = 2.40  # kHz

        self._build_ui()
        self.player.start()

    def _build_ui(self):
        # Frequency display
        freq_frame = tk.Frame(self, bg="#c0c0c0")
        freq_frame.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        self.freq_var = tk.StringVar(value="7100.00")
        tk.Entry(freq_frame, textvariable=self.freq_var, font=("Courier", 18, "bold"),
                 width=10, justify="right").pack(side=tk.LEFT)
        tk.Label(freq_frame, text="kHz", bg="#c0c0c0").pack(side=tk.LEFT, padx=2)

        for label in ["A", "B", "A-B"]:
            tk.Button(freq_frame, text=label, width=3, command=lambda l=label: self._mem(l)).pack(side=tk.LEFT, padx=1)

        # Tuning buttons
        tune_frame = tk.Frame(self, bg="#c0c0c0")
        tune_frame.pack(fill=tk.X, padx=4)
        for step, txt in [(-100, "---"), (-10, "--"), (-1, "-"), (0.1, ".0"),
                          (1, "+"), (10, "++"), (100, "+++")]:
            tk.Button(tune_frame, text=txt, width=3,
                      command=lambda s=step: self._tune(s)).pack(side=tk.LEFT, padx=1)

        # Modes
        mode_frame = tk.Frame(self, bg="#c0c0c0")
        mode_frame.pack(fill=tk.X, padx=4, pady=2)
        self.mode_var = tk.StringVar(value="USB")
        for m in ["CW", "LSB", "USB", "AM", "FM", "AMsync"]:
            tk.Radiobutton(mode_frame, text=m, variable=self.mode_var, value=m,
                           bg="#c0c0c0", indicatoron=0, width=6,
                           command=self._set_mode).pack(side=tk.LEFT, padx=1)

        # Gain + mute
        gain_frame = tk.Frame(self, bg="#c0c0c0")
        gain_frame.pack(fill=tk.X, padx=4)
        tk.Label(gain_frame, text="Gain:", bg="#c0c0c0").pack(side=tk.LEFT)
        self.gain_scale = tk.Scale(gain_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                   length=120, command=self._gain, bg="#c0c0c0")
        self.gain_scale.set(50)
        self.gain_scale.pack(side=tk.LEFT)
        self.mute_var = tk.BooleanVar()
        tk.Checkbutton(gain_frame, text="mute", variable=self.mute_var,
                       command=self._mute, bg="#c0c0c0").pack(side=tk.LEFT, padx=8)

        # Right side controls
        right = tk.Frame(self, bg="#c0c0c0")
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=8)

        filt_frame = tk.Frame(right, bg="#c0c0c0")
        filt_frame.pack()
        tk.Label(filt_frame, text="Filter:", bg="#c0c0c0").pack(side=tk.LEFT)
        self.filt_var = tk.StringVar(value="2.40 kHz")
        tk.Label(filt_frame, textvariable=self.filt_var, bg="#c0c0c0").pack(side=tk.LEFT)
        tk.Button(filt_frame, text="narrower", command=lambda: self._filter(-0.2)).pack(side=tk.LEFT)
        tk.Button(filt_frame, text="wider", command=lambda: self._filter(+0.2)).pack(side=tk.LEFT)

        opts = tk.Frame(right, bg="#c0c0c0")
        opts.pack(pady=4)
        for txt in ["squelch", "autonotch", "noise reduction"]:
            tk.Checkbutton(opts, text=txt, bg="#c0c0c0").pack(anchor="w")

        tk.Button(right, text="Audio recording  start", command=self._record).pack(pady=4)

        # Connection bar
        conn = tk.Frame(self, bg="#c0c0c0")
        conn.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=4)
        tk.Label(conn, text="KiwiSDR:", bg="#c0c0c0").pack(side=tk.LEFT)
        self.host_var = tk.StringVar(value="kiwisdr.example.com:8073")
        tk.Entry(conn, textvariable=self.host_var, width=28).pack(side=tk.LEFT, padx=2)
        tk.Button(conn, text="Connect", command=self._connect).pack(side=tk.LEFT)
        tk.Button(conn, text="Disconnect", command=self._disconnect).pack(side=tk.LEFT, padx=2)

        # Decoder buttons
        dec = tk.Frame(self, bg="#c0c0c0")
        dec.pack(side=tk.BOTTOM, fill=tk.X, padx=4)
        tk.Button(dec, text="Morse Decode", command=self._morse).pack(side=tk.LEFT)
        tk.Button(dec, text="SSTV Record", command=self._sstv).pack(side=tk.LEFT, padx=4)
        tk.Button(dec, text="WeFAX Record", command=self._wefax).pack(side=tk.LEFT)

    def _connect(self):
        hostport = self.host_var.get().strip()
        if ":" in hostport:
            host, port = hostport.split(":")
            port = int(port)
        else:
            host, port = hostport, 8073
        try:
            self.client = KiwiClient(host, port)
            self.client.audio_callback = self._on_audio
            self.client.connect()
            self.client.set_freq(self.freq)
            messagebox.showinfo("OK", "Connected")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _disconnect(self):
        if self.client:
            self.client.close()
            self.client = None

    def _on_audio(self, samples, smeter):
        self.player.feed(samples)
        # optional: feed decoders here
        if hasattr(self, "_morse_active") and self._morse_active:
            self.morse.process(samples)

    def _tune(self, step):
        self.freq = round(self.freq + step, 2)
        self.freq_var.set(f"{self.freq:.2f}")
        if self.client:
            self.client.set_freq(self.freq)

    def _set_mode(self):
        self.mode = self.mode_var.get().lower()
        # simple passband defaults
        pb = {"cw": ( -200, 200), "lsb": (-2700, -300), "usb": (300, 2700),
              "am": (-3000, 3000), "fm": (-5000, 5000), "amsync": (-3000, 3000)}
        lc, hc = pb.get(self.mode, (300, 2700))
        if self.client:
            self.client.set_mod(self.mode, lc, hc, self.freq)

    def _filter(self, delta):
        self.filter_bw = max(0.5, min(10.0, self.filter_bw + delta))
        self.filt_var.set(f"{self.filter_bw:.2f} kHz")
        # apply roughly centered
        half = self.filter_bw * 500
        if self.mode in ("lsb",):
            lc, hc = -half*2, -300
        else:
            lc, hc = 300, half*2
        if self.client:
            self.client.set_passband(int(lc), int(hc))

    def _gain(self, val):
        self.player.set_gain(float(val) / 50.0)

    def _mute(self):
        self.player.set_mute(self.mute_var.get())

    def _record(self):
        messagebox.showinfo("Record", "Recording starts – implement file writer if needed")

    def _morse(self):
        self._morse_active = True
        messagebox.showinfo("Morse", "Morse decoder active (console / expand UI)")

    def _sstv(self):
        if not self.sstv.recording:
            self.sstv.start()
            messagebox.showinfo("SSTV", "Recording for SSTV… press again to save")
        else:
            fn = self.sstv.stop_and_save()
            messagebox.showinfo("SSTV", f"Saved {fn}\nFeed to external SSTV decoder")

    def _wefax(self):
        # identical pattern
        pass

    def _mem(self, which):
        pass  # A/B memory placeholders

    def on_closing(self):
        self._disconnect()
        self.player.stop()
        self.destroy()

if __name__ == "__main__":
    app = MiniKiwiGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
