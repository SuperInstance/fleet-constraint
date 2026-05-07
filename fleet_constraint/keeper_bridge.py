"""KeeperBridge — cocapn-glue-core protocol for Keeper ↔ Fleet communication."""

from typing import Dict, Optional, Callable
import struct
import msgpack
import socket
import threading
import time


class MessageType:
    """Message types matching cocapn-glue-core protocol."""
    HEARTBEAT = 0x01
    STATUS = 0x02
    COMMAND = 0x03
    RESPONSE = 0x04
    TILE = 0x05
    ALERT = 0x06
    REGISTER = 0x07
    DEREGISTER = 0x08


class KeeperBridge:
    """
    Bridge for communicating with the Keeper via cocapn-glue-core protocol.

    Implements the wire protocol used by cocapn-glue-core — sends tiles to
    the Keeper and receives commands from the Keeper.

    Usage:
        bridge = KeeperBridge()
        bridge.connect("keeper.cocapn.local", 8901)
        bridge.send_tile({"tile_id": "t1", "data": "..."})
        cmd = bridge.receive_command()
    """

    def __init__(self, agent_id: str = "fleet-agent", timeout: float = 5.0):
        self.agent_id = agent_id
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.sequence = 0
        self.handlers: Dict[int, Callable] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def connect(self, addr: str, port: int) -> bool:
        """
        Connect to the Keeper at the given address.

        Args:
            addr: Keeper hostname or IP
            port: Keeper port

        Returns:
            True if connection succeeded
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((addr, port))
            self._running = True
            return True
        except (socket.error, ConnectionRefusedError) as e:
            self.socket = None
            return False

    def _encode(self, msg_type: int, payload: Dict) -> bytes:
        """Encode a message in wire format: [4-byte length][msgpack payload]."""
        data = msgpack.packb(
            {
                "t": msg_type,
                "p": payload,
                "ts": time.time(),
                "s": self.agent_id,
                "n": self.sequence,
            },
            use_bin_type=True,
        )
        self.sequence += 1
        return struct.pack(">I", len(data)) + data

    def _decode(self, data: bytes) -> Optional[Dict]:
        """Decode a wire-format message."""
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception:
            return None

    def send_tile(self, tile: Dict) -> bool:
        """
        Send a tile to the Keeper via the TILE message type.

        Args:
            tile: Dictionary representing the tile payload

        Returns:
            True if send succeeded
        """
        if not self.socket:
            return False
        try:
            wire_data = self._encode(MessageType.TILE, tile)
            self.socket.sendall(wire_data)
            return True
        except (socket.error, BrokenPipeError):
            self.socket = None
            return False

    def receive_command(self) -> Optional[Dict]:
        """
        Receive a command from the Keeper (blocking).

        Returns:
            Decoded command dict, or None if no data available
        """
        if not self.socket:
            return None
        try:
            # Read 4-byte length prefix
            len_bytes = self.socket.recv(4)
            if not len_bytes or len(len_bytes) < 4:
                return None
            msg_len = struct.unpack(">I", len_bytes)[0]

            # Read payload
            payload_bytes = b""
            while len(payload_bytes) < msg_len:
                chunk = self.socket.recv(msg_len - len(payload_bytes))
                if not chunk:
                    return None
                payload_bytes += chunk

            decoded = self._decode(payload_bytes)
            if decoded and decoded.get("t") == MessageType.COMMAND:
                return decoded.get("p", {})
            return None
        except socket.timeout:
            return None
        except (socket.error, BrokenPipeError):
            self.socket = None
            return None

    def send_heartbeat(self) -> bool:
        """Send a heartbeat to the Keeper."""
        if not self.socket:
            return False
        try:
            wire_data = self._encode(MessageType.HEARTBEAT, {"status": "ok"})
            self.socket.sendall(wire_data)
            return True
        except (socket.error, BrokenPipeError):
            self.socket = None
            return False

    def close(self):
        """Close the connection to the Keeper."""
        self._running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
