import sounddevice as sd
import numpy as np 

SAMPLE_R = 48000
CHANNELS = 1                         #mono cause phone has two mics 
BLOCK_SIZE = 1024                  #std

def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"Status: {status}")

    rms = np.sqrt(np.mean(indata**2))  # RMS signal val
    peak = np.max(np.abs(indata))        # peak signal val

    
    print(f"\rRMS: {rms:.4f}, Peak: {peak:.4f}", end="", flush=True)



if __name__ == "__main__":
    print("Avail Audio dev: ")
    print(sd.query_devices())

    for i, dev in enumerate(sd.query_devices()):
        if dev['max_input_channels'] > 0:
            if "(hw:" in dev['name'] or "Built-in Audio" in dev['name']:
                print(f"{i}: {dev['name']}")

    device = int(input("\n Enter Device index: "))
    print("\n Listening : ctrl c stop....")
    
    try:
        with sd.InputStream(
            device = device, 
            samplerate = SAMPLE_R, 
            channels = CHANNELS, 
            blocksize = BLOCK_SIZE,
            dtype = "float32",
            callback = audio_callback):

            while True:
                sd.sleep(1000)
    except KeyboardInterrupt:
        print("\nRecording stopped by user.....")