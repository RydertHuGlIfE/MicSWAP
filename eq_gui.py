
from __future__ import annotations
import json, subprocess, sys, threading, time
from pathlib import Path
import numpy as np
from pedalboard import Pedalboard, LowShelfFilter, PeakFilter, HighShelfFilter, Compressor, Reverb, Gain, Limiter
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QSlider, QCheckBox, QGroupBox, QMessageBox

RATE, BLOCK_SAMPLES = 48000, 960
BLOCK_BYTES = BLOCK_SAMPLES * 2
INPUT_SOURCE, OUTPUT_SINK, OUTPUT_SOURCE = "micswap_mic", "MICSWAP_EQ_SINK", "MICSWAP_EQ_MIC"
SETTINGS_FILE = Path(__file__).with_name("micswap_settings.json")
DEFAULT = {"last_preset":"broadcast", "custom":{"low_db":8.9,"mid_db":-8.3,"high_db":6.6,"mid_frequency":5000}, "gain_db":0.4, "reverb_enabled":False, "reverb_amount":0.08}





PRESETS = {
 "natural":{"label":"1 Natural","low_db":0,"mid_db":0,"high_db":0,"mid_frequency":2500},
 "warm":{"label":"2 Warm","low_db":4,"mid_db":-2,"high_db":-1,"mid_frequency":1800},
 "broadcast":{"label":"3 Broadcast","low_db":3,"mid_db":-3,"high_db":4,"mid_frequency":3500},
 "gaming":{"label":"4 Gaming","low_db":2,"mid_db":-4,"high_db":5,"mid_frequency":4000},
 "bright":{"label":"5 Bright","low_db":1,"mid_db":1,"high_db":6,"mid_frequency":4500},
 "custom":{"label":"6 Custom","low_db":8.9,"mid_db":-8.3,"high_db":6.6,"mid_frequency":5000}}





def load_settings():
    s=json.loads(json.dumps(DEFAULT))
    try:
        d=json.loads(SETTINGS_FILE.read_text())
        if isinstance(d,dict):
            s["last_preset"]=d.get("last_preset",s["last_preset"])
            for k in ("gain_db","reverb_enabled","reverb_amount"):
                s[k]=d.get(k,s[k])
            if isinstance(d.get("custom"),dict): s["custom"].update(d["custom"])
    except (OSError,ValueError,TypeError): pass
    if s["last_preset"] not in PRESETS: s["last_preset"]="broadcast"
    for k in ("low_db","mid_db","high_db"): s["custom"][k]=max(-12,min(12,float(s["custom"][k])))
    s["custom"]["mid_frequency"]=max(100,min(8000,int(s["custom"]["mid_frequency"])))
    s["gain_db"]=max(-24,min(12,float(s["gain_db"])))
    s["reverb_amount"]=max(0,min(.5,float(s["reverb_amount"])))
    return s

def save_settings(s):
    tmp=SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8"); tmp.replace(SETTINGS_FILE)

def get_devices():
    sinks=subprocess.run(["pactl","list","short","sinks"],capture_output=True,text=True,check=True).stdout
    sources=subprocess.run(["pactl","list","short","sources"],capture_output=True,text=True,check=True).stdout
    return ({x.split()[1] for x in sinks.splitlines() if len(x.split())>1}, {x.split()[1] for x in sources.splitlines() if len(x.split())>1})

def ensure_devices():
    sinks,sources=get_devices()
    if OUTPUT_SINK not in sinks:
        subprocess.run(["pactl","load-module","module-null-sink",f"sink_name={OUTPUT_SINK}","sink_properties=device.description=MicSWAP_EQ_SINK"],check=True,capture_output=True,text=True)
    _,sources=get_devices()
    if OUTPUT_SOURCE not in sources:
        subprocess.run(["pactl","load-module","module-remap-source",f"master={OUTPUT_SINK}.monitor",f"source_name={OUTPUT_SOURCE}","source_properties=device.description=MicSWAP_EQ_MIC"],check=True,capture_output=True,text=True)

class Effects:
    def __init__(self,s):
        self.lock=threading.RLock()
        self.low=LowShelfFilter(cutoff_frequency_hz=200,gain_db=0)
        self.mid=PeakFilter(cutoff_frequency_hz=s["custom"]["mid_frequency"],gain_db=0,q=1)
        self.high=HighShelfFilter(cutoff_frequency_hz=8000,gain_db=0)
        self.comp=Compressor(threshold_db=-24,ratio=1.5,attack_ms=69,release_ms=2160)
        self.reverb=Reverb(room_size=.25,damping=.5,wet_level=0,dry_level=1,width=1)
        self.gain=Gain(gain_db=s["gain_db"]); self.limiter=Limiter(threshold_db=-1,release_ms=100)
        self.board=Pedalboard([self.low,self.mid,self.high,self.comp,self.reverb,self.gain,self.limiter])
        self.set_eq(s["custom"]); self.set_reverb(s["reverb_enabled"],s["reverb_amount"])
    def set_eq(self,v):
        with self.lock:
            self.low.gain_db=float(v["low_db"]); self.mid.gain_db=float(v["mid_db"])
            self.mid.cutoff_frequency_hz=float(v["mid_frequency"]); self.high.gain_db=float(v["high_db"])
    def set_gain(self,v):
        with self.lock: self.gain.gain_db=float(v)
    def set_reverb(self,on,amount):
        with self.lock: self.reverb.wet_level=float(amount) if on else 0.0; self.reverb.dry_level=1.0
    def process(self,raw):
        a=np.frombuffer(raw,dtype="<i2").astype(np.float32).reshape(1,-1)/32768.0
        with self.lock: out=self.board(a,RATE,reset=False)
        return np.clip(np.nan_to_num(out[0])*32767,-32768,32767).astype("<i2").tobytes()

class AudioWorker(threading.Thread):
    def __init__(self,e): super().__init__(daemon=True); self.e=e; self.stop_event=threading.Event(); self.procs=[]; self.error=None
    def stop(self):
        self.stop_event.set()
        for p in self.procs:
            if p.poll() is None: p.terminate()
    def run(self):
        try:
            cap=subprocess.Popen(["parec","--raw","--format=s16le",f"--rate={RATE}","--channels=1",f"--device={INPUT_SOURCE}"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
            play=subprocess.Popen(["pacat","--playback","--raw","--format=s16le",f"--rate={RATE}","--channels=1",f"--device={OUTPUT_SINK}"],stdin=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
            self.procs=[cap,play]; pending=b""
            while not self.stop_event.is_set():
                chunk=cap.stdout.read(BLOCK_BYTES-len(pending))
                if not chunk:
                    if cap.poll() is not None: raise RuntimeError(cap.stderr.read().decode(errors="replace"))
                    time.sleep(.002); continue
                pending+=chunk
                if len(pending)<BLOCK_BYTES: continue
                block,pending=pending[:BLOCK_BYTES],pending[BLOCK_BYTES:]
                play.stdin.write(self.e.process(block)); play.stdin.flush()
                if play.poll() is not None: raise RuntimeError(play.stderr.read().decode(errors="replace"))
        except Exception as ex:
            if not self.stop_event.is_set(): self.error=str(ex) or repr(ex)
        finally:
            for p in self.procs:
                if p.poll() is None:
                    p.terminate()
                    try: p.wait(timeout=1)
                    except Exception: p.kill()

class SliderRow(QWidget):
    def __init__(self,name,lo,hi,value,suffix):
        super().__init__(); self.suffix=suffix; self.name=QLabel(name); self.slider=QSlider(Qt.Orientation.Horizontal); self.slider.setRange(lo,hi); self.slider.setValue(int(round(value))); self.val=QLabel(); self.val.setMinimumWidth(70); self.val.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        l=QHBoxLayout(self); l.setContentsMargins(0,2,0,2); l.addWidget(self.name,2); l.addWidget(self.slider,5); l.addWidget(self.val,1); self.slider.valueChanged.connect(self.label); self.label(self.slider.value())
    def label(self,v): self.val.setText(f"{v}{self.suffix}")

class Window(QWidget):
    def __init__(self):
        super().__init__(); self.s=load_settings(); self.fx=Effects(self.s); self.audio=None; self.buttons={}; self.setWindowTitle("MicSWAP — Live Effects"); self.resize(720,650); self.setMinimumWidth(620)
        self.setStyleSheet("QWidget{background:#101516;color:#e7eeee;font-size:13px} QGroupBox{border:1px solid #303b3d;border-radius:8px;margin-top:12px;padding:12px} QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 5px} QPushButton{background:#30383a;border:1px solid #4b5557;border-radius:7px;padding:12px;text-align:left} QPushButton:checked{border:1px solid #00d58a;background:#142622} QSlider::groove:horizontal{height:5px;background:#394446;border-radius:2px} QSlider::handle:horizontal{background:#00d58a;width:14px;margin:-5px 0;border-radius:7px}")
        root=QVBoxLayout(self); title=QLabel("MicSWAP"); title.setStyleSheet("font-size:22px;font-weight:700"); root.addWidget(title); root.addWidget(QLabel("Live microphone effects · Press 1–6 to switch presets"))
        pg=QGroupBox("Presets"); grid=QGridLayout(pg); grid.setSpacing(8)
        for i,(key,info) in enumerate(PRESETS.items()):
            b=QPushButton(info["label"]); b.setCheckable(True); b.clicked.connect(lambda checked=False,k=key:self.apply_preset(k)); self.buttons[key]=b; grid.addWidget(b,i//2,i%2)
        root.addWidget(pg)
        eg=QGroupBox("Equalizer"); el=QVBoxLayout(eg); self.hint=QLabel(); el.addWidget(self.hint)
        self.low = SliderRow("Low", -12, 12, 0, " dB")
        self.mid = SliderRow("Mid", -12, 12, 0, " dB")
        self.high = SliderRow("High", -12, 12, 0, " dB")
        self.freq = SliderRow("Mid sweep", 100, 8000, 3500, " Hz")

        for row in (self.low, self.mid, self.high, self.freq):
            el.addWidget(row)
            row.slider.valueChanged.connect(self.eq_changed)

        root.addWidget(eg)

        og = QGroupBox("Output")
        ol = QVBoxLayout(og)
        self.gain = SliderRow("Gain", -24, 12, self.s["gain_db"], " dB")
        ol.addWidget(self.gain)
        self.gain.slider.valueChanged.connect(self.gain_changed)

        self.reverb_check = QCheckBox("Enable reverb")
        self.reverb_check.setChecked(self.s["reverb_enabled"])
        ol.addWidget(self.reverb_check)

        self.reverb_amount = SliderRow(
            "Reverb amount", 0, 50,
            int(self.s["reverb_amount"] * 100), "%"
        )
        ol.addWidget(self.reverb_amount)
        self.reverb_check.toggled.connect(self.reverb_changed)
        self.reverb_amount.slider.valueChanged.connect(self.reverb_changed)

        root.addWidget(og)

        self.status = QLabel("Starting audio...")
        root.addWidget(self.status)

        self.apply_preset(self.s["last_preset"], initial=True)

        self.audio = AudioWorker(self.fx)
        self.audio.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_audio)
        self.timer.start(500)

    def apply_preset(self, key, initial=False):
        values = self.s["custom"] if key == "custom" else PRESETS[key]
        self.s["last_preset"] = key

        for row, k in (
            (self.low, "low_db"),
            (self.mid, "mid_db"),
            (self.high, "high_db"),
            (self.freq, "mid_frequency"),
        ):
            row.slider.blockSignals(True)
            row.slider.setValue(int(round(values[k])))
            row.slider.blockSignals(False)
            row.label(row.slider.value())
            row.slider.setEnabled(key == "custom")

        self.hint.setText(
            "Custom EQ — sliders editable and auto-saved."
            if key == "custom"
            else "Select 6 Custom to edit the EQ."
        )

        self.eq_changed()
        for name, button in self.buttons.items():
            button.setChecked(name == key)

        self.save()

    def eq_changed(self, *_):
        values = {
            "low_db": self.low.slider.value(),
            "mid_db": self.mid.slider.value(),
            "high_db": self.high.slider.value(),
            "mid_frequency": self.freq.slider.value(),
        }
        self.fx.set_eq(values)

        if self.s["last_preset"] == "custom":
            self.s["custom"] = values
            self.save()

    def gain_changed(self, value):
        self.s["gain_db"] = value
        self.fx.set_gain(value)
        self.save()

    def reverb_changed(self, *_):
        enabled = self.reverb_check.isChecked()
        amount = self.reverb_amount.slider.value() / 100
        self.s["reverb_enabled"] = enabled
        self.s["reverb_amount"] = amount
        self.fx.set_reverb(enabled, amount)
        self.save()

    def save(self):
        try:
            save_settings(self.s)
        except OSError as e:
            self.status.setText(f"Settings save failed: {e}")

    def check_audio(self):
        if self.audio and self.audio.is_alive():
            self.status.setText(
                f"Live: {INPUT_SOURCE} → {OUTPUT_SOURCE}"
            )
        elif self.audio and self.audio.error:
            self.timer.stop()
            QMessageBox.critical(self, "Audio error", self.audio.error)

    def keyPressEvent(self, event: QKeyEvent):
        if Qt.Key.Key_1 <= event.key() <= Qt.Key.Key_6:
            self.apply_preset(list(PRESETS.keys())[event.key() - Qt.Key.Key_1])
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.audio:
            self.audio.stop()
            self.audio.join(timeout=2)
        event.accept()


def main():
    app = QApplication(sys.argv)

    try:
        ensure_devices()
        _, sources = get_devices()

        if INPUT_SOURCE not in sources:
            QMessageBox.critical(
                None,
                "MicSWAP input missing",
                f"'{INPUT_SOURCE}' not found.\n"
                "Start audiobackend.py and pccomp.py first."
            )
            return 1

        window = Window()
        window.show()
        return app.exec()

    except Exception as e:
        QMessageBox.critical(None, "MicSWAP error", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
    
