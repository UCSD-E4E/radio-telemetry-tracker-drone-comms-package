"""Unit tests for the packet transceiver module handling radio packet transmission and acknowledgments."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from radio_telemetry_tracker_drone_comms_package.proto.packets_pb2 import RadioPacket
from radio_telemetry_tracker_drone_comms_package.transceiver import (
    PacketManager,
    _current_timestamp_us,
)

# Test constants
DEFAULT_ACK_TIMEOUT = 2.0
DEFAULT_MAX_RETRIES = 5
TEST_ACK_TIMEOUT = 0.1
TEST_MAX_RETRIES = 1
TEST_PACKET_ID = 100
TEST_ACK_ID = 101


class MockRadioInterface:
    """Mock implementation of radio interface for testing."""

    def connect(self) -> None:
        """Connect to the mock radio interface."""

    def close(self) -> None:
        """Close the mock radio interface connection."""

    def send_packet(self, packet: RadioPacket) -> None:
        """Send a packet through the mock radio interface."""

    def receive_packet(self) -> None | RadioPacket:
        """Receive a packet from the mock radio interface."""
        return None


def test_current_timestamp_us() -> None:
    """Test that current timestamp function returns valid integer microseconds."""
    ts = _current_timestamp_us()
    assert isinstance(ts, int)  # noqa: S101
    assert ts > 0  # noqa: S101


def test_packet_manager_initialization() -> None:
    """Test PacketManager initialization with default parameters."""
    radio = MockRadioInterface()
    manager = PacketManager(radio_interface=radio)
    assert manager.radio_interface is radio  # noqa: S101
    assert manager.ack_timeout == DEFAULT_ACK_TIMEOUT  # noqa: S101
    assert manager.max_retries == DEFAULT_MAX_RETRIES  # noqa: S101
    assert manager.on_ack_timeout is None  # noqa: S101


def test_packet_manager_start_stop() -> None:
    """Test PacketManager start and stop operations."""
    radio = MagicMock()
    manager = PacketManager(radio_interface=radio)
    manager.start()
    radio.connect.assert_called_once()
    assert manager._send_thread.is_alive()  # noqa: S101, SLF001
    assert manager._recv_thread.is_alive()  # noqa: S101, SLF001

    manager.stop()
    radio.close.assert_called_once()
    assert not manager._send_thread.is_alive()  # noqa: S101, SLF001
    assert not manager._recv_thread.is_alive()  # noqa: S101, SLF001


def test_packet_manager_enqueue() -> None:
    """Test packet enqueuing with priority based on acknowledgment requirement."""
    radio = MockRadioInterface()
    manager = PacketManager(radio_interface=radio)
    pkt = RadioPacket()
    pkt.ack_pkt.base.need_ack = True
    manager.enqueue_packet(pkt)

    # PriorityQueue item => (priority, enq_time, packet)
    item = manager.send_queue.get_nowait()
    assert item[0] == 0  # Priority 0 for need_ack=True  # noqa: S101
    assert item[2] is pkt  # noqa: S101


def test_packet_manager_ack_handling() -> None:
    """Test acknowledgment handling with timeout and retry logic."""
    radio = MockRadioInterface()
    manager = PacketManager(
        radio_interface=radio,
        ack_timeout=TEST_ACK_TIMEOUT,
        max_retries=TEST_MAX_RETRIES,
    )

    # Start the manager
    manager.start()
    try:
        # Enqueue a packet that needs ack
        pkt = RadioPacket()
        pkt.ack_pkt.base.packet_id = TEST_PACKET_ID
        pkt.ack_pkt.base.need_ack = True
        manager.enqueue_packet(pkt)

        # Let the send loop run
        time.sleep(0.2)

        # Expect that the packet is in outstanding_acks
        assert TEST_PACKET_ID in manager.outstanding_acks  # noqa: S101

        # Wait for retry logic
        time.sleep(0.2)

        # Because max_retries=1, after 1 retry it should time out
        # and remove the packet from outstanding_acks
        assert TEST_PACKET_ID not in manager.outstanding_acks  # noqa: S101
    finally:
        manager.stop()


def test_packet_manager_handle_incoming_ack() -> None:
    """Test handling of incoming acknowledgment packets."""
    radio = MockRadioInterface()
    manager = PacketManager(radio_interface=radio)
    pkt = RadioPacket()
    pkt.cfg_rqt.base.packet_id = TEST_ACK_ID
    pkt.cfg_rqt.base.need_ack = True

    manager.outstanding_acks[TEST_ACK_ID] = {
        "packet": pkt,
        "send_time": time.time(),
        "retries": 0,
    }

    # Make an ack packet
    ack = RadioPacket()
    ack.ack_pkt.ack_id = TEST_ACK_ID

    manager._handle_incoming_packet(ack)  # noqa: SLF001
    assert TEST_ACK_ID not in manager.outstanding_acks  # noqa: S101
