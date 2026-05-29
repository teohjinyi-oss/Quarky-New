"""
Tests for v2 Infrastructure: Protocol, TCP Transport
"""

import pytest
from runtime.infrastructure.protocol import (
    MessageType, ProtocolMessage,
    chat_request, status_request, notification,
)


class TestProtocol:
    def test_message_types(self):
        assert len(MessageType) == 10

    def test_chat_request(self):
        msg = chat_request("hello")
        assert msg.type == MessageType.CHAT
        assert msg.payload["text"] == "hello"

    def test_status_request(self):
        msg = status_request()
        assert msg.type == MessageType.STATUS

    def test_notification(self):
        msg = notification("Alert", "CPU high", priority="warning")
        assert msg.type == MessageType.NOTIFICATION
        assert msg.payload["priority"] == "warning"

    def test_encode_decode_roundtrip(self):
        msg = chat_request("hello world")
        encoded = msg.to_bytes()
        assert isinstance(encoded, bytes)
        decoded = ProtocolMessage.from_bytes(encoded)
        assert decoded.type == MessageType.CHAT
        assert decoded.payload["text"] == "hello world"

    def test_decode_partial(self):
        msg = chat_request("hello")
        encoded = msg.to_bytes()
        # Only give first 2 bytes — should fail gracefully
        with pytest.raises(Exception):
            ProtocolMessage.from_bytes(encoded[:2])

    def test_roundtrip_json(self):
        msg = chat_request("test message")
        json_str = msg.to_json()
        decoded = ProtocolMessage.from_json(json_str)
        assert decoded.type == MessageType.CHAT
        assert decoded.payload["text"] == "test message"
        assert decoded.id == msg.id
