from pedalboard import Compressor
import numpy as np 


SAMPLE_RATE = 48000

PRESETS = {
    "natural": {
        "threshold_db": -20.0,
        "ratio": 2.0,
        "attack_ms": 10.0,
        "release_ms": 100.0,
    },
    "voice_chat": {
        "threshold_db": -24.0,
        "ratio": 3.0,
        "attack_ms": 5.0,
        "release_ms": 100.0,
    },
    "strong": {
        "threshold_db": -30.0,
        "ratio": 4.0,
        "attack_ms": 3.0,
        "release_ms": 150.0,
    },
}

class MicCompressor:
    def __init__(self, preset="voice_chat"):
        self.effect = None
        self.set_preset(preset)

    def set_preset(self, preset):
        if preset not in PRESETS:
            raise ValueError(
                f"Unknown preset: {preset}. "
                f"Choose from {list(PRESETS)}"
            )

        settings = PRESETS[preset]
        self.effect = Compressor(
            threshold_db=settings["threshold_db"],
            ratio=settings["ratio"],
            attack_ms=settings["attack_ms"],
            release_ms=settings["release_ms"],
        )

    def set_custom(
        self,
        threshold_db=-24.0,
        ratio=3.0,
        attack_ms=5.0,
        release_ms=100.0,
    ):
        self.effect = Compressor(
            threshold_db=threshold_db,
            ratio=ratio,
            attack_ms=attack_ms,
            release_ms=release_ms,
        )

    
    def process(self, pcm_data):
        if not pcm_data:
            return pcm_data

        # Process only complete 16-bit samples
        usable_bytes = len(pcm_data) - (len(pcm_data) % 2)
        if usable_bytes == 0:
            return pcm_data

        samples = np.frombuffer(
            pcm_data[:usable_bytes],
            dtype="<i2"
        )

        # Convert PCM to float32, shape: (channels, samples)
        audio = (
            samples.astype(np.float32) / 32768.0
        )[None, :]

        # Apply compressor
        processed = self.effect(audio, SAMPLE_RATE)

        # Extract mono channel BEFORE checking length
        processed = processed[0]

        # Ensure output sample count matches input
        if len(processed) != len(samples):
            processed = processed[:len(samples)]

            if len(processed) < len(samples):
                processed = np.pad(
                    processed,
                    (0, len(samples) - len(processed))
                )

        # Convert back to signed 16-bit PCM
        processed = np.clip(
            processed,
            -1.0,
            32767 / 32768
        )

        output = (processed * 32768.0).astype("<i2")

        # Preserve any trailing incomplete byte
        return output.tobytes() + pcm_data[usable_bytes:]