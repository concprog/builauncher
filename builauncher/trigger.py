"""The client: send a message to the daemon. No Qt, so it starts fast."""
import socket

from .system import PIPE, WINDOWS, socket_path

TRIGGER, STOP = b"trigger", b"stop"


def send(message: bytes) -> bool:
    """Send message to the running daemon over its socket or pipe. False if none runs."""
    try:
        if WINDOWS:
            with open(PIPE, "wb") as pipe:
                pipe.write(message)
        else:
            with socket.socket(socket.AF_UNIX) as client:
                client.connect(str(socket_path()))
                client.sendall(message)
    except OSError:
        return False
    return True
