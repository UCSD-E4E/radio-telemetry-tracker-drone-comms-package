"""Packet encoding and decoding utilities for radio telemetry communications."""

from __future__ import annotations

import google.protobuf.message

from radio_telemetry_tracker_drone_comms_package.proto import RadioPacket

SYNC_MARKER = b"\xAA\x55"
SYNC_MARKER_LENGTH = len(SYNC_MARKER)
LENGTH_FIELD_SIZE = 4  # Size of the length field in bytes
CHECKSUM_SIZE = 2  # Size of the CRC-CCITT checksum in bytes


def _calculate_crc16_ccitt(data: bytes) -> int:
    """Calculate a 16-bit CRC-CCITT checksum."""
    crc = 0xFFFF
    poly = 0x1021
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


class RadioCodec:
    """Provides static methods to encode and decode RadioPacket messages."""

    @staticmethod
    def encode_packet(packet: RadioPacket) -> bytes:
        """Encode a RadioPacket into a byte array with the sync marker, length header, and CRC-CCITT."""
        message_data = packet.SerializeToString()
        length = len(message_data)

        # data_without_checksum = SYNC_MARKER + LENGTH(4 bytes) + MESSAGE_DATA
        header = SYNC_MARKER + length.to_bytes(LENGTH_FIELD_SIZE, byteorder="big")
        data_without_checksum = header + message_data

        checksum_val = _calculate_crc16_ccitt(data_without_checksum)
        checksum_bytes = checksum_val.to_bytes(CHECKSUM_SIZE, byteorder="big")
        return data_without_checksum + checksum_bytes

    @staticmethod
    def decode_packet(data: bytes) -> RadioPacket | None:
        """Decode a byte array into a RadioPacket, validating sync marker, length, and CRC-CCITT."""
        min_length = (
            SYNC_MARKER_LENGTH + LENGTH_FIELD_SIZE + CHECKSUM_SIZE
        )  # sync + length + checksum
        if len(data) >= min_length and data[:SYNC_MARKER_LENGTH] == SYNC_MARKER:
            length = int.from_bytes(
                data[SYNC_MARKER_LENGTH : SYNC_MARKER_LENGTH + LENGTH_FIELD_SIZE],
                "big",
            )
            expected_length = (
                SYNC_MARKER_LENGTH + LENGTH_FIELD_SIZE + length + CHECKSUM_SIZE
            )
            if len(data) == expected_length:
                message_data = data[
                    SYNC_MARKER_LENGTH
                    + LENGTH_FIELD_SIZE : SYNC_MARKER_LENGTH
                    + LENGTH_FIELD_SIZE
                    + length
                ]
                checksum_in = int.from_bytes(
                    data[
                        SYNC_MARKER_LENGTH
                        + LENGTH_FIELD_SIZE
                        + length : SYNC_MARKER_LENGTH
                        + LENGTH_FIELD_SIZE
                        + length
                        + CHECKSUM_SIZE
                    ],
                    "big",
                )

                # Verify checksum
                if (
                    _calculate_crc16_ccitt(
                        data[: SYNC_MARKER_LENGTH + LENGTH_FIELD_SIZE + length],
                    )
                    == checksum_in
                ):
                    # Decode Protobuf
                    try:
                        packet = RadioPacket()
                        packet.ParseFromString(message_data)
                    except google.protobuf.message.DecodeError:
                        return None
                    return packet
        return None
