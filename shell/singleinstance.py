"""복수 선택 취합: 첫 인스턴스가 서버가 되어 형제들의 파일 경로를 모은다.
tkinter 미의존, 루프백 소켓만 사용."""
import os
import socket
import threading
import time

_MAGIC = b"IMGDIET1\n"


def coalesce(argv_files, port=51737, window=0.8):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt":
        try:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        except (AttributeError, OSError):
            pass
    else:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("127.0.0.1", port))
        srv.listen(16)
    except OSError:
        srv.close()
        return _send_to_server(argv_files, port)

    # 서버: 형제 연결을 window초 동안 수신
    collected = list(argv_files)
    deadline = [time.time() + window]
    lock = threading.Lock()
    stop = threading.Event()

    def accept_loop():
        srv.settimeout(0.1)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                conn.settimeout(0.5)
                data = b""
                while b"\n" not in data[len(_MAGIC):] or not data.startswith(_MAGIC):
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 65536:
                        break
                if data.startswith(_MAGIC):
                    payload = data[len(_MAGIC):].decode("utf-8", "replace")
                    with lock:
                        for line in payload.splitlines():
                            if line:
                                collected.append(line)
                        deadline[0] = time.time() + 0.25  # 새 파일 오면 조금 연장
            except OSError:
                pass
            finally:
                conn.close()

    th = threading.Thread(target=accept_loop, daemon=True)
    th.start()
    while True:
        with lock:
            d = deadline[0]
        if time.time() >= d:
            break
        time.sleep(0.05)
    stop.set()
    srv.close()
    th.join(1.0)
    with lock:
        return list(collected)


def _send_to_server(argv_files, port):
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        c.settimeout(1.0)
        c.connect(("127.0.0.1", port))
        payload = _MAGIC + ("\n".join(argv_files) + "\n").encode("utf-8")
        c.sendall(payload)
        return None
    except OSError:
        return list(argv_files)  # 우리 서버가 아니면 폴백: 단독 창
    finally:
        c.close()
