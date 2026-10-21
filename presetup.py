import shutil 
import subprocess
import platform 

REQUIRED_TOOLS = ["pactl", "adb"]

def check_tool(name):
    path = shutil.which(name)

    if path:
        print(f"[OK] {name} at {path}")
        return True

    print(f"[MISSING] {name} not found in PATH")


def get_audio_server():
    if not shutil.which("pactl"):
        print("[MISSING] pactl not found in PATH")
        return None

    
    try:
        result = subprocess.run(
            ["pactl", "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            print(f"[ERROR] pactl info failed: {result.stderr.strip()}")
            print(result.stderr.strip())
            return None

        for line in result.stdout.splitlines():
            if line.startswith("Server Name:"):
                server_name = line.split(":", 1)[1].strip()
                return server_name

    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[ERROR] Audio server check failed: {exc}")

    return None



def check_android_device():
    """Check whether an Android device is connected through ADB."""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )

        devices = [
            line.split()[0]
            for line in result.stdout.splitlines()[1:]
            if len(line.split()) >= 2
            and line.split()[1] == "device"
        ]

        if devices:
            print(f"[OK] Found {len(devices)} authorized Android device(s).")
            return True

        print("[WAIT] No authorized Android device found.")
        print("Connect your phone and enable USB debugging.")
        return False

    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[ERROR] ADB check failed: {exc}")
        return False


def check_audio_capabilities():
    """Check whether PipeWire tools are available."""
    for tool in ("pw-cli", "pw-loopback"):
        path = shutil.which(tool)

        if path:
            print(f"[OK] {tool}: {path}")
        else:
            print(f"[INFO] {tool} not found; checking alternatives may be needed.")


def main():
    print("=== MicSWAP Presetup ===")
    print(f"Operating system: {platform.system()}")

    print("\n--- Android device ---")
    check_android_device()

    print("\n--- Audio capabilities ---")
    check_audio_capabilities()

    print("\n--- Required tools ---")
    tools_ok = True

    for tool in REQUIRED_TOOLS:
        if not check_tool(tool):
            tools_ok = False

    print("\n--- Audio system ---")
    server = get_audio_server()

    if server:
        print(f"[OK] Audio server: {server}")
    else:
        print("[ERROR] Audio server unavailable.")
        tools_ok = False

    print("\n--- Result ---")
    if tools_ok:
        print("Presetup checks passed.")
    else:
        print("Some checks failed. Resolve them before continuing.")


if __name__ == "__main__":
    main()

