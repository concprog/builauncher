"""One running launcher: listen on a Unix socket for triggers from `builauncher`."""
from collections.abc import Callable

from PySide6.QtNetwork import QLocalServer

from .trigger import TRIGGER, socket_path


def serve(on_trigger: Callable[[], None]) -> QLocalServer:
    """Listen for triggers. Keep the result alive."""
    path = str(socket_path())
    QLocalServer.removeServer(path)  # a socket left by a crash
    server = QLocalServer()
    if not server.listen(path):
        raise OSError(f"{path}: {server.errorString()}")

    def accept() -> None:
        while conn := server.nextPendingConnection():
            conn.readyRead.connect(lambda c=conn: c.readAll().data() == TRIGGER and on_trigger())
            conn.disconnected.connect(conn.deleteLater)

    server.newConnection.connect(accept)
    return server
