import subprocess

def detect_device():
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, check=True
        )

        devices = []


        for line in result.stdout.splitlines()[1:]:
            parts = line.split()

            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
            
        return devices 
    except subprocess.CalledProcessError as e:
        print(f"Error executing adb command: {e}")
        return []





if __name__ == "__main__":
    devices = detect_device()

    if devices:
        print("Connected mobile devices: ")
        for device in devices:
            print(f" - {devices}")
    else:
        print("No auth device found")