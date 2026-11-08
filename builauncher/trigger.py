"""The hotkey client: send a trigger to the daemon. No Qt, so it starts fast."""
import socket

from .system import PIPE, WINDOWS, socket_path

TRIGGER = b"trigger"


def send_trigger() -> bool:
    """Trigger the running daemon over its socket or pipe. False if none runs."""
    try:
        if WINDOWS:
            with open(PIPE, "wb") as pipe:
                pipe.write(TRIGGER)
        else:
            with socket.socket(socket.AF_UNIX) as client:
                client.connect(str(socket_path()))
                client.sendall(TRIGGER)
    except OSError:
        return False
    return True
