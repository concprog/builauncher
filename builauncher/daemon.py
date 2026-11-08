"""One running launcher: listen on a Unix socket (a named pipe on Windows) for triggers and stop."""
from collections.abc import Callable

from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalServer

from .system import server_name
from .trigger import STOP, TRIGGER


def serve(on_trigger: Callable[[], None]) -> QLocalServer:
    """Listen for triggers. Keep the result alive."""
    path = server_name()
    QLocalServer.removeServer(path)  # a socket left by a crash
    server = QLocalServer()
    if not server.listen(path):
        raise OSError(f"{path}: {server.errorString()}")

    handlers = {TRIGGER: on_trigger, STOP: QCoreApplication.quit}

    def read(message: bytes) -> None:
        if handler := handlers.get(message):
            handler()

    def accept() -> None:
        while conn := server.nextPendingConnection():
            conn.readyRead.connect(lambda c=conn: read(c.readAll().data()))
            conn.disconnected.connect(conn.deleteLater)

    server.newConnection.connect(accept)
    return server
