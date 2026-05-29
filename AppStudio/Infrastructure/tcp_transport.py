"""
Infrastructure: TCP Transport Server (v2)

TCP socket server for JavaFX GUI ↔ Python backend communication.
Handles connection lifecycle, message framing, and dispatch.

The server runs in a background thread, accepts one GUI client
connection at a time, and dispatches received messages to
registered handlers.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from typing import Callable, Optional

from AppStudio.Config import GUI
from AppStudio.Infrastructure.protocol import (
    ProtocolMessage,
    MessageType,
    read_message_from_buffer,
    heartbeat_response,
    error_response,
)


# Type alias for message handlers
MessageHandler = Callable[[ProtocolMessage], Optional[ProtocolMessage]]


class TCPTransport:
    """
    TCP server for GUI communication.

    Listens on configured host:port, accepts a single client connection
    (the JavaFX GUI), and handles message exchange using the protocol module.
    """

    def __init__(
        self,
        host: str = "",
        port: int = 0,
        max_message_size: int = 1_048_576,
    ):
        self._host = host or GUI.get("protocol_host", "127.0.0.1")
        self._port = port or GUI.get("protocol_port", 9400)
        self._max_size = max_message_size
        self._handlers: dict[MessageType, MessageHandler] = {}
        self._server: Optional[socket.socket] = None
        self._client: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._heartbeat_interval = GUI.get("heartbeat_interval", 5.0)

    def register_handler(self, msg_type: MessageType, handler: MessageHandler) -> None:
        """Register a handler for a message type."""
        self._handlers[msg_type] = handler

    def start(self) -> None:
        """Start the TCP server in a background thread."""
        if self._running:
            return

        self._running = True
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.settimeout(1.0)
        self._server.bind((self._host, self._port))
        self._server.listen(1)

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the TCP server."""
        self._running = False
        if self._client:
            try:
                self._client.close()
            except OSError:
                pass
            self._client = None
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None

    def send(self, message: ProtocolMessage) -> bool:
        """Send a message to the connected GUI client."""
        if not self._client:
            return False
        try:
            data = message.to_bytes()
            self._client.sendall(data)
            return True
        except (OSError, BrokenPipeError):
            self._client = None
            return False

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def address(self) -> tuple[str, int]:
        return (self._host, self._port)

    # ── Internal ────────────────────────────────────────────

    def _accept_loop(self) -> None:
        """Accept client connections."""
        while self._running and self._server:
            try:
                client, addr = self._server.accept()
                self._client = client
                self._client.settimeout(1.0)
                self._handle_client()
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    time.sleep(0.5)

    def _handle_client(self) -> None:
        """Handle messages from a connected client."""
        buffer = b""

        while self._running and self._client:
            try:
                data = self._client.recv(4096)
                if not data:
                    break
                buffer += data

                while buffer:
                    msg, buffer = read_message_from_buffer(buffer)
                    if msg is None:
                        break
                    self._dispatch(msg)

            except socket.timeout:
                continue
            except (OSError, ConnectionResetError):
                break

        self._client = None

    def _dispatch(self, msg: ProtocolMessage) -> None:
        """Dispatch a received message to registered handler."""
        # Handle heartbeat internally
        if msg.type == MessageType.HEARTBEAT:
            self.send(heartbeat_response(msg.id))
            return

        handler = self._handlers.get(msg.type)
        if handler:
            try:
                response = handler(msg)
                if response:
                    self.send(response)
            except Exception as e:
                self.send(error_response(str(e), reply_to=msg.id))
        else:
            self.send(error_response(
                f"No handler for message type: {msg.type.value}",
                reply_to=msg.id,
            ))
