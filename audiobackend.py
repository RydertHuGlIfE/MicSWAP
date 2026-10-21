
import subprocess
import time

SINK_MODULE = "module-null-sink"
SOURCE_MODULE = "module-remap-source"

SINK_NAME = "null-sink"
MONITOR_NAME = f"{SINK_NAME}.monitor"
SOURCE_NAME = "micswap_mic"

SINK_DESCRIPTION = "MicSWAP_Virtual_Mic"
SOURCE_DESCRIPTION = "MicSWAP_Microphone"

created_sink_module = None
created_source_module = None


def run_command(command):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[ERROR] Command failed: {exc}")
        return None


def list_sources():
    result = run_command(["pactl", "list", "short", "sources"])
    if result is None or result.returncode != 0:
        return None
    return result.stdout


def source_exists(source_name):
    sources = list_sources()

    if sources is None:
        return False

    return any(
        len(fields := line.split()) >= 2
        and fields[1] == source_name
        for line in sources.splitlines()
    )


def create_virtual_sink():
    global created_sink_module

    if source_exists(MONITOR_NAME):
        print(f"[OK] Existing monitor found: {MONITOR_NAME}")
        return True

    result = run_command([
        "pactl",
        "load-module",
        SINK_MODULE,
        f"sink_name={SINK_NAME}",
        f"sink_properties=device.description={SINK_DESCRIPTION}",
        "rate=48000",
        "channels=1",
    ])

    if result is None or result.returncode != 0:
        print("[ERROR] Could not create virtual sink.")
        if result:
            print(result.stderr.strip())
        return False

    created_sink_module = result.stdout.strip()
    print(f"[OK] Virtual sink created: module {created_sink_module}")

    if not source_exists(MONITOR_NAME):
        print(f"[ERROR] Monitor not found: {MONITOR_NAME}")
        return False

    return True


def create_virtual_source():
    global created_source_module

    if source_exists(SOURCE_NAME):
        print(f"[OK] Existing microphone found: {SOURCE_NAME}")
        return True

    result = run_command([
        "pactl",
        "load-module",
        SOURCE_MODULE,
        f"master={MONITOR_NAME}",
        f"source_name={SOURCE_NAME}",
        f"source_properties=device.description={SOURCE_DESCRIPTION}",
    ])

    if result is None or result.returncode != 0:
        print("[ERROR] Could not create virtual microphone.")
        if result:
            print(result.stderr.strip())
        return False

    created_source_module = result.stdout.strip()
    print(f"[OK] Virtual microphone created: module {created_source_module}")

    if not source_exists(SOURCE_NAME):
        print(f"[ERROR] Microphone source not found: {SOURCE_NAME}")
        return False

    return True


def remove_module(module_id, description):
    if module_id is None:
        return

    result = run_command(["pactl", "unload-module", module_id])

    if result is not None and result.returncode == 0:
        print(f"[OK] Removed {description}: module {module_id}")
    else:
        print(f"[WARN] Could not remove {description}: module {module_id}")
        if result:
            print(result.stderr.strip())


def cleanup():
    global created_sink_module, created_source_module

    # Remove only modules created by this run.
    # Source must be removed before its parent sink.
    remove_module(created_source_module, "virtual microphone")
    created_source_module = None

    remove_module(created_sink_module, "virtual sink")
    created_sink_module = None


def main():
    print("--- MicSWAP audio backend ---")

    try:
        if not create_virtual_sink():
            return

        if not create_virtual_source():
            return

        print("\n[OK] MicSWAP microphone is ready.")
        print("Keep this process running while using MicSWAP.")
        print("Press Ctrl+C to shut down the backend.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Shutting down MicSWAP audio backend.")

    finally:
        cleanup()
        print("[INFO] Backend stopped.")


if __name__ == "__main__":
    main()
