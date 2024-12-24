"""Unit tests for protobuf module initialization and message imports."""

import sys

from pytest_mock import MockerFixture


def test_proto_init_calls_compiler(mocker: MockerFixture) -> None:
    """Test that ensure_proto_compiled() is invoked automatically when the proto/__init__.py module is imported."""
    mock_compiler = mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.ensure_proto_compiled",
        autospec=True,
    )

    # Force a reload to trigger the import-time side effect
    if "radio_telemetry_tracker_drone_comms_package.proto.__init__" in sys.modules:
        del sys.modules["radio_telemetry_tracker_drone_comms_package.proto.__init__"]

    import radio_telemetry_tracker_drone_comms_package.proto.__init__  # noqa: F401

    mock_compiler.assert_called_once()


def test_protobuf_messages_are_imported() -> None:
    """Test that protobuf message classes are imported and accessible."""
    from radio_telemetry_tracker_drone_comms_package.proto import (
        AckPacket,
        BasePacket,
        RadioPacket,
    )

    # Instantiate some classes
    ack_packet = AckPacket()
    base_packet = BasePacket()
    radio_packet = RadioPacket()

    assert ack_packet is not None  # noqa: S101
    assert base_packet is not None  # noqa: S101
    assert radio_packet is not None  # noqa: S101
