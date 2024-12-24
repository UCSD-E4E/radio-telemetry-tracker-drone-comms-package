"""Protocol buffer module for radio telemetry packet definitions."""

from radio_telemetry_tracker_drone_comms_package.proto.compiler import ensure_proto_compiled

# Ensure proto files are compiled before importing
ensure_proto_compiled()

# Now import the generated protobuf
from radio_telemetry_tracker_drone_comms_package.proto.packets_pb2 import (  # noqa: E402
    AckPacket,
    BasePacket,
    ConfigRequestPacket,
    ConfigResponsePacket,
    ErrorPacket,
    GPSPacket,
    LocEstPacket,
    PingPacket,
    RadioPacket,
    StartRequestPacket,
    StartResponsePacket,
    StopRequestPacket,
    StopResponsePacket,
    SyncRequestPacket,
    SyncResponsePacket,
)

__all__ = [
    "AckPacket",
    "BasePacket",
    "ConfigRequestPacket",
    "ConfigResponsePacket",
    "ErrorPacket",
    "GPSPacket",
    "LocEstPacket",
    "PingPacket",
    "RadioPacket",
    "StartRequestPacket",
    "StartResponsePacket",
    "StopRequestPacket",
    "StopResponsePacket",
    "SyncRequestPacket",
    "SyncResponsePacket",
]
