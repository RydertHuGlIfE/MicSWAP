
import subprocess
import threading
import queue

SAMPLE_RATE = 48000
CHANNELS = 1
SAMPLE_WIDTH = 2

FRAME_MS = 20
FRAME_BYTES = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * FRAME_MS // 1000
PREBUFFER_FRAMES = 5


class AudioOutput:
    def __init__(self, sink_name="null-sink"):
        self.sink_name = sink_name
        self.process = None
        self.audio_queue = queue.Queue(maxsize=100)
        self.worker = None
        self.running = False

    def start(self):
        self.process = subprocess.Popen(
            [
                "pw-play",
                "--raw",
                "--format", "s16",
                "--rate", str(SAMPLE_RATE),
                "--channels", str(CHANNELS),
                "--target", self.sink_name,
                "-",
            ],
            stdin=subprocess.PIPE,
            bufsize=0,
        )

        self.running = True
        self.worker = threading.Thread(
            target=self._audio_worker,
            daemon=True,
        )
        self.worker.start()

        print(f"[OK] Audio output started: {self.sink_name}")

    def write(self, data):
        if not self.running:
            return

        try:
            self.audio_queue.put(data, timeout=0.1)
        except queue.Full:
            print("[WARN] Audio queue full; incoming audio delayed/dropped")

    def _audio_worker(self):
        buffer = bytearray()
        started = False

        try:
            while self.running or not self.audio_queue.empty():
                try:
                    data = self.audio_queue.get(timeout=0.05)
                    buffer.extend(data)
                except queue.Empty:
                    continue

                if not started:
                    if len(buffer) < FRAME_BYTES * PREBUFFER_FRAMES:
                        continue
                    started = True
                    print("[OK] Audio prebuffer filled")

                while len(buffer) >= FRAME_BYTES:
                    frame = buffer[:FRAME_BYTES]
                    del buffer[:FRAME_BYTES]

                    if self.process.poll() is not None:
                        print("[ERROR] pw-play exited")
                        self.running = False
                        return

                    self.process.stdin.write(frame)
                    self.process.stdin.flush()

        except (BrokenPipeError, OSError) as exc:
            if self.running:
                print(f"[ERROR] Audio output: {exc}")

    def stop(self):
        self.running = False

        if self.worker:
            self.worker.join(timeout=2)

        if self.process:
            if self.process.stdin:
                self.process.stdin.close()

            self.process.wait()
            self.process = None

        print("[OK] Audio output stopped")
