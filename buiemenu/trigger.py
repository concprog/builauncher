"""The hotkey client: send a trigger to the daemon. No Qt, so it starts fast."""
import os
import socket
from pathlib import Path

TRIGGER = b"trigger"


def socket_path() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/buiemenu-{os.getuid()}") / "buiemenu.sock"


def send_trigger() -> bool:
    """Trigger the running daemon. False if none runs."""
    with socket.socket(socket.AF_UNIX) as client:
        try:
            client.connect(str(socket_path()))
        except OSError:
            return False
        client.sendall(TRIGGER)
        return True
