import socket 

HOST = "127.0.0.1"
PORT = 50005
CHUNK_SIZE = 4096                  #same as main 

def main():
    print(f"reciever on {HOST}:{PORT}")
    print("waiting for dev")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
                            break
                        t_byt += len(data)    

                        if t_byt and t_byt % 48000 < CHUNK_SIZE:
                            print(
                                f"\rReceived {total_bytes / 96000:.1f} seconds "
                                f"of audio ({total_bytes} bytes)",
                                end="",
                                flush=True,
                            )
                print(f"\nconn closed at {addr}, {t_byt}")

            except Exception as e:
                print(f"\nconn error at {addr}: {e}")
                conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped it rn")