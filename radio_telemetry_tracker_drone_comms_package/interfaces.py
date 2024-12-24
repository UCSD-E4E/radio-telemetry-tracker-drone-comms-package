"""Radio interface implementations for drone communications.

This module provides:
- Abstract base class RadioInterface
- SerialRadioInterface
- SimulatedRadioInterface
"""

from __future__ import annotations

import abc
import logging
import time
from typing import TYPE_CHECKING

from radio_telemetry_tracker_drone_comms_package.codec import (
    CHECKSUM_SIZE,
    LENGTH_FIELD_SIZE,
    SYNC_MARKER,
    SYNC_MARKER_LENGTH,
    RadioCodec,
)

if TYPE_CHECKING:
    from radio_telemetry_tracker_drone_comms_package.proto.packets_pb2 import (
        RadioPacket,
    )

logger = logging.getLogger(__name__)


class RadioInterface(abc.ABC):
    """Abstract base class for radio communication interfaces."""

    def __init__(self, read_timeout: float = 1.0) -> None:
        """Initialize radio interface with specified read timeout.

        Args:
            read_timeout: Maximum time in seconds to wait for read operations.
        """
        self.read_timeout = read_timeout

    @abc.abstractmethod
    def connect(self) -> None:
        """Connect to the radio device (real or simulated)."""

    @abc.abstractmethod
    def _send_data(self, data: bytes) -> None:
        """Send raw bytes through the radio interface."""

    @abc.abstractmethod
    def _read_data(self, max_bytes: int) -> bytes:
        """Read raw bytes from the underlying interface."""

    @abc.abstractmethod
    def close(self) -> None:
        """Close the radio interface connection."""

    def send_packet(self, packet: RadioPacket) -> None:
        """Encode and send a RadioPacket through the interface."""
        data = RadioCodec.encode_packet(packet)
        self._send_data(data)

    def receive_packet(self) -> RadioPacket | None:
        """Receive raw bytes from the interface and decode a RadioPacket."""
        # Read the sync marker first
        sync = self._read_with_timeout(SYNC_MARKER_LENGTH)
        if len(sync) < SYNC_MARKER_LENGTH:
            return None
        if sync != SYNC_MARKER:
            return None

        # Read length field
        length_bytes = self._read_with_timeout(LENGTH_FIELD_SIZE)
        if len(length_bytes) < LENGTH_FIELD_SIZE:
            return None
        msg_len = int.from_bytes(length_bytes, byteorder="big")

        # Read message data
        message_data = self._read_with_timeout(msg_len)
        if len(message_data) < msg_len:
            return None

        # Read checksum
        checksum_bytes = self._read_with_timeout(CHECKSUM_SIZE)
        if len(checksum_bytes) < CHECKSUM_SIZE:
            return None

        # Reconstruct the entire packet for decode
        raw_packet = sync + length_bytes + message_data + checksum_bytes
        return RadioCodec.decode_packet(raw_packet)

    def _read_with_timeout(self, num_bytes: int) -> bytes:
        """Read a specified number of bytes with an overall time limit."""
        deadline = time.time() + self.read_timeout
        data_collected = bytearray()

        while len(data_collected) < num_bytes:
            if time.time() > deadline:
                break
            chunk = self._read_data(num_bytes - len(data_collected))
            if chunk:
                data_collected.extend(chunk)
            else:
                time.sleep(0.01)

        return bytes(data_collected)


class SerialRadioInterface(RadioInterface):
    """Radio interface using serial communication."""

    def __init__(self, port: str, baudrate: int = 56700, timeout: float = 1.0) -> None:
        """Initialize serial radio interface.

        Args:
            port: Serial port name
            baudrate: Communication speed in bits per second
            timeout: Read timeout in seconds
        """
        super().__init__(read_timeout=timeout)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self) -> None:
        """Initialize and open the serial connection with configured parameters."""
        import serial

        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def _send_data(self, data: bytes) -> None:
        if self.ser and self.ser.is_open:
            self.ser.write(data)

    def _read_data(self, max_bytes: int) -> bytes:
        if self.ser and self.ser.is_open:
            return self.ser.read(max_bytes)
        return b""

    def close(self) -> None:
        """Close the serial connection if it is open."""
        if self.ser and self.ser.is_open:
            self.ser.close()


class SimulatedRadioInterface(RadioInterface):
    """Radio interface using TCP/IP for simulation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 50000,
        *,
        server_mode: bool = False,
        timeout: float = 1.0,
    ) -> None:
        """Initialize simulated radio interface using TCP/IP.

        Args:
            host: IP address or hostname to connect/bind to
            port: TCP port number
            server_mode: If True, act as server; if False, act as client
            timeout: Read timeout in seconds
        """
        super().__init__(read_timeout=timeout)
        self.host = host
        self.port = port
        self.server_mode = server_mode
        self.sock = None
        self.conn = None

    def connect(self) -> None:
        """Establish TCP/IP connection in either client or server mode."""
        import socket

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if self.server_mode:
            self.sock.bind((self.host, self.port))
            self.sock.listen(1)
            logger.info("Waiting for connection on %s:%d...", self.host, self.port)

            # Set socket to non-blocking mode
            self.sock.setblocking(False)  # noqa: FBT003
            while True:
                try:
                    self.conn, addr = self.sock.accept()
                    logger.info("Client connected from %s:%d", addr[0], addr[1])
                    # Set normal timeout for subsequent operations
                    self.conn.settimeout(self.read_timeout)
                    break
                except BlockingIOError:
                    time.sleep(0.1)  # Sleep briefly to avoid busy-waiting
                except Exception:
                    logger.exception("Error accepting connection")
                    self.close()
                    raise
        else:
            try:
                self.sock.settimeout(10.0)  # 10 seconds for client connection
                self.sock.connect((self.host, self.port))
                self.conn = self.sock
                self.conn.settimeout(self.read_timeout)
                logger.info("Connected to server %s:%d", self.host, self.port)
            except (socket.timeout, ConnectionRefusedError):
                logger.exception("Failed to connect to server")
                self.close()
                raise

    def _send_data(self, data: bytes) -> None:
        if self.conn:
            self.conn.sendall(data)

    def _read_data(self, max_bytes: int) -> bytes:
        if self.conn:
            try:
                return self.conn.recv(max_bytes)
            except (TimeoutError, ConnectionError, OSError):
                return b""
        return b""

    def close(self) -> None:
        """Close both the connection and socket if they exist."""
        if self.conn:
            self.conn.close()
        if self.sock:
            self.sock.close()
