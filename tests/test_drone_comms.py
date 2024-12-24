"""Unit tests for the DroneComms class handling radio communication with the drone."""
from __future__ import annotations

from typing import Protocol

import pytest

from radio_telemetry_tracker_drone_comms_package.data_models import (
    ConfigRequestData,
    ConfigResponseData,
    SyncRequestData,
)
from radio_telemetry_tracker_drone_comms_package.drone_comms import (
    DroneComms,
    RadioConfig,
)
from radio_telemetry_tracker_drone_comms_package.proto.packets_pb2 import RadioPacket


class MockInterface(Protocol):
    """Protocol for mock radio interface."""

    def connect(self) -> None:
        """Connect to the radio interface."""
        ...

    def close(self) -> None:
        """Close the radio interface connection."""
        ...

    def send_packet(self, packet: RadioPacket) -> None:
        """Send a packet over the radio interface."""
        ...

    def receive_packet(self) -> None | RadioPacket:
        """Receive a packet from the radio interface."""
        ...


@pytest.fixture
def mock_radio_interface() -> MockInterface:
    """Create a mock radio interface for testing."""

    class MockImpl:
        def connect(self) -> None:
            pass

        def close(self) -> None:
            pass

        def send_packet(self, packet: RadioPacket) -> None:
            pass

        def receive_packet(self) -> None:
            return None

    return MockImpl()


@pytest.fixture
def drone_comms(mock_radio_interface: MockInterface) -> DroneComms:
    """Create a DroneComms instance with mock radio interface for testing."""
    cfg = RadioConfig(interface_type="serial", port="COM3", baudrate=9600)
    comms = DroneComms(radio_config=cfg)
    # Inject the mock interface
    comms.radio_interface = mock_radio_interface
    return comms


def test_drone_comms_init_missing_config() -> None:
    """Test DroneComms initialization fails when config is missing."""
    with pytest.raises(ValueError, match="Radio config is required"):
        DroneComms(None)


def test_drone_comms_init_serial_port_missing() -> None:
    """Test DroneComms initialization fails when serial port is missing."""
    cfg = RadioConfig(interface_type="serial", port=None)
    with pytest.raises(ValueError, match="Serial port must be specified"):
        DroneComms(cfg)


def test_drone_comms_init_invalid_interface() -> None:
    """Test DroneComms initialization fails with invalid interface type."""
    cfg = RadioConfig(interface_type="unknown")
    with pytest.raises(ValueError, match="Invalid interface type"):
        DroneComms(cfg)


def test_drone_comms_send_sync_request(drone_comms: DroneComms) -> None:
    """Test sending sync request returns valid packet ID and timestamp."""
    pid, need_ack, timestamp = drone_comms.send_sync_request(SyncRequestData())
    assert need_ack is True  # noqa: S101
    assert pid != 0  # noqa: S101
    assert timestamp != 0  # noqa: S101


def test_drone_comms_send_config_request(drone_comms: DroneComms) -> None:
    """Test sending config request with all parameters."""
    data = ConfigRequestData(
        gain=1.1,
        sampling_rate=32000,
        center_frequency=1234,
        run_num=2,
        enable_test_data=True,
        ping_width_ms=5,
        ping_min_snr=10,
        ping_max_len_mult=2.0,
        ping_min_len_mult=1.0,
        target_frequencies=[100, 200],
    )
    pid, need_ack, timestamp = drone_comms.send_config_request(data)
    assert need_ack is True  # noqa: S101
    assert pid != 0  # noqa: S101
    assert timestamp != 0  # noqa: S101


def test_drone_comms_register_and_invoke_handler(drone_comms: DroneComms) -> None:
    """Test registering and invoking config response handler."""
    # Test registering a config response handler, then simulating reception
    results = []

    def on_config_response(resp: ConfigResponseData) -> None:
        results.append(resp.success)

    drone_comms.register_config_response_handler(on_config_response)

    # Simulate a RadioPacket containing ConfigResponsePacket
    rp = RadioPacket()
    rp.cfg_rsp.base.packet_id = 999
    rp.cfg_rsp.base.timestamp = 123456
    rp.cfg_rsp.success = True

    # Simulate that DroneComms receives this packet
    drone_comms.on_user_packet_received(rp)

    assert len(results) == 1  # noqa: S101
    assert results[0] is True  # noqa: S101
