"""Unit tests for the radio codec module."""

from radio_telemetry_tracker_drone_comms_package.codec import (
    RadioCodec,
    _calculate_crc16_ccitt,
)
from radio_telemetry_tracker_drone_comms_package.proto.packets_pb2 import RadioPacket

# Test constants
CRC16_CCITT_REF_VALUE = 0x29B1
TEST_PACKET_ID = 1234
TEST_TIMESTAMP = 999999
TEST_ACK_ID = 5678


def test_calculate_crc16_ccitt() -> None:
    """Test CRC16-CCITT calculation against known reference value."""
    data = b"123456789"  # Classic check data for CRC
    assert _calculate_crc16_ccitt(data) == CRC16_CCITT_REF_VALUE  # noqa: S101


def test_encode_decode_packet() -> None:
    """Test packet encoding and decoding with a simple acknowledgment packet."""
    packet = RadioPacket()
    packet.ack_pkt.base.packet_id = TEST_PACKET_ID
    packet.ack_pkt.base.need_ack = False
    packet.ack_pkt.base.timestamp = TEST_TIMESTAMP
    packet.ack_pkt.ack_id = TEST_ACK_ID

    encoded = RadioCodec.encode_packet(packet)
    assert encoded.startswith(b"\xAA\x55")  # noqa: S101

    decoded = RadioCodec.decode_packet(encoded)
    assert decoded is not None  # noqa: S101
    assert decoded.ack_pkt.base.packet_id == TEST_PACKET_ID  # noqa: S101
    assert decoded.ack_pkt.ack_id == TEST_ACK_ID  # noqa: S101


def test_decode_packet_invalid_sync_marker() -> None:
    """Test packet decoding with invalid sync marker returns None."""
    data = b"\x00\x11\x22\x33"
    result = RadioCodec.decode_packet(data)
    assert result is None  # noqa: S101


def test_decode_packet_truncated() -> None:
    """Test packet decoding with truncated data returns None."""
    data = b"\xAA\x55\x00\x00\x00\x05"  # length=5 but we won't supply the 5 bytes + checksum
    result = RadioCodec.decode_packet(data)
    assert result is None  # noqa: S101


def test_decode_packet_bad_checksum() -> None:
    """Test packet decoding with corrupted checksum returns None."""
    packet = RadioPacket()
    packet.ping_pkt.base.packet_id = 10
    encoded = RadioCodec.encode_packet(packet)

    # Corrupt the last two bytes (the CRC)
    corrupted = encoded[:-2] + b"\x00\x00"
    result = RadioCodec.decode_packet(corrupted)
    assert result is None  # noqa: S101

