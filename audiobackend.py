import subprocess

MODULE_NAME = "module-null-sink"
SINK_NAME = "null-sink"

def run_command(command):
    return subprocess.run(
        command, 
        capture_output = True,
        text=True,
        timeout=10,
    )

def create_virtual_mic():
    #virtual audio sink
    result = run_command([
        "pactl",
        "load-module",
        MODULE_NAME,
        f"name={SINK_NAME}"
        "sink_properties=device.description=MicSWAP_Virtual_Mic"
        "rate=48000",
        "channels=1"
    ])

    if result.returncode != 0:
        print(f"error: mic not create {result.stderr.strip()}")
        return None

    module_id = result.stdout.strip()
    print(f"ok VAD ready {module_id}")
    return module_id


def verify_virtual_mic():
    result = run_command([
        "pactl", "list", "short", "sources"
    ])

    if result.returncode != 0:
        print(f"Error listing sources: {result.stderr.strip()}")
        return False

    print("Available audio sources:")
    print(result.stdout)

    expected_source = f"{SINK_NAME}.monitor"

    for line in result.stdout.splitlines():
        fields = line.split()

        if len(fields) >= 2 and fields[1] == expected_source:
            print(f"Linux detected: {expected_source}")
            print(line)
            return True

    print(f"Virtual source not found: {expected_source}")
    return False



def remove_virtual_mic(module_id):
    result = run_command([
        "pactl", "unload-module", module_id
    ])

    if result.returncode == 0:
        print("VAD removed")
    else:
        print("VAD cant be removed error")
        print(result.stderr.strip())



def main():
    print("---micswap backend test---")

    module_id = create_virtual_mic()

    if not module_id:
        return

    try:
        if verify_virtual_mic():
            print("VAD sink monitor source pass. phone feed not yet")
            input("Press Enter to remove virtual mic...")
    except KeyboardInterrupt:
        print("interrupted test")
    
    finally:
        remove_virtual_mic(module_id)


if __name__ == "__main__":
    main()
        