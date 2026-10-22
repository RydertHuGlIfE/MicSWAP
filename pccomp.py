import socket 
from audio_output import AudioOutput
import time
import subprocess

HOST = "127.0.0.1"
PORT = 50005
CHUNK_SIZE = 4096                  #same as main 

def main():
    print(f"reciever on {HOST}:{PORT}")
    print("waiting for dev")
    audio = AudioOutput("null-sink")
    audio.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)

        while True:
            conn, addr = s.accept()
            print(f"conn at {addr}")

            t_byt = 0

            try:
                with conn:
                    while True:
                        data = conn.recv(CHUNK_SIZE) #raw 48khz, 16bit lilendianPCM
                        if not data:
                            print("closed", flush=True)
                            break
                        else:
                            audio.write(data)
                        t_byt += len(data)    

                        now = time.monotonic()
                        last_log = 0

                        if now - last_log >= 1:
                                print(
                                    f"\rReceived {t_byt / 96000:.1f} seconds "
                                    f"of audio ({t_byt} bytes)",
                                    end="",
                                    flush=True,
                                )
                                last_log = now
                            
                print(f"\nconn closed at {addr}, {t_byt}")

            except (ConnectionError, OSError) as exc:
                    print(f"\nSocket error: {exc}", flush=True)

            print(f"\nSession total: {t_byt} bytes", flush=True)


if __name__ == "__main__":
    try:
    
        cmd1 = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True)

        if cmd1.returncode != 0:
            print("[ERROR] ADB command failed.")
            raise SystemExit(1)

        devices = [
            line.split()[0]
            for line in cmd1.stdout.splitlines()[1:]
            if len(line.split()) >= 2
            and line.split()[1] == "device"
        ]

        if not devices:
            print("[ERROR] No authorized Android device found.")
            raise SystemExit(1)

        command = subprocess.run(
            ["adb", "reverse", "tcp:50005", "tcp:50005"],
            capture_output=True,
            text=True
        )

        if command.returncode != 0:
            print("[ERROR] ADB reverse failed:")
            print(command.stderr.strip())
            raise SystemExit(1)

        print("[OK] ADB reverse configured: tcp:50005")
        main()

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")