
import numpy as np
from compressor import MicCompressor

compressor = MicCompressor("voice_chat")

# Generate a one-second test tone at 48 kHz.
t = np.arange(48000) / 48000
tone = 0.8 * np.sin(2 * np.pi * 440 * t)

pcm = (tone * 32767).astype("<i2").tobytes()
result = compressor.process(pcm)

print("Input bytes:", len(pcm))
print("Output bytes:", len(result))
print("Output format:", "48 kHz, mono, signed 16-bit PCM")

assert len(result) == len(pcm)
print("[OK] Compressor test passed")
