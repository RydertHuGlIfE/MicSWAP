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


    print(f"RMS: {rms:.4f}, Peak: {peak:.4f}")

    devices = int(input("\n Enter Device index"))
    print("\n LIstening : ctrl c stop....")



if __name__ == "__main__":
    print("Avail Audio dev: ")
    print(sd.query_devices())

    device = int(input("\n Enter Device index: "))
    print("\n Listening : ctrl c stop....")
    
    try:
        with sd.InputStream(
            device = devices, 
            samplerate = SAMPLE_R, 
            channels = CHANNELS, 
            blocksize = BLOCK_SIZE,
            dtype = "float32",
            callback = audio_callback):

            while True:
                sd.sleep(1000)
    except KeyboardInterrupt:
        print("\nRecording stopped by user.....")