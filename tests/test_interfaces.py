"""Unit tests for radio interface implementations including serial and simulated modes."""

import socket
from unittest.mock import MagicMock, call, patch

import pytest

from radio_telemetry_tracker_drone_comms_package.interfaces import (
    RadioInterface,
    SerialRadioInterface,
    SimulatedRadioInterface,
)

# Test constants
EXPECTED_CLOSE_CALLS = 2  # Both self.sock and self.conn close in client mode


def test_radio_interface_abstract() -> None:
    """RadioInterface is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        RadioInterface()


@patch("serial.Serial")
def test_serial_radio_interface(mock_serial: MagicMock) -> None:
    """Test that SerialRadioInterface connect() calls serial.Serial with correct args."""
    interface = SerialRadioInterface(port="COM3", baudrate=9600, timeout=2.0)
    interface.connect()
    mock_serial.assert_called_once_with("COM3", 9600, timeout=2.0)

    # Mock a read
    mock_serial.return_value.read.return_value = b"abc"
    data = interface._read_data(3)  # noqa: SLF001
    assert data == b"abc"  # noqa: S101

    interface.close()
    mock_serial.return_value.close.assert_called_once()


@patch("socket.socket")
def test_simulated_radio_interface_client_mode(mock_socket: MagicMock) -> None:
    """Test SimulatedRadioInterface in client mode connects to server."""
    mock_sock_instance = mock_socket.return_value
    interface = SimulatedRadioInterface(host="testhost", port=12345, server_mode=False)
    interface.connect()

    mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
    assert mock_sock_instance.settimeout.call_args_list == [  # noqa: S101
        call(10.0),  # Connection timeout
        call(1.0),  # Read timeout
    ]
    mock_sock_instance.connect.assert_called_once_with(("testhost", 12345))

    interface.close()
    # In client mode, both self.sock and self.conn point to the same socket
    assert mock_sock_instance.close.call_count == EXPECTED_CLOSE_CALLS  # noqa: S101


@patch("socket.socket")
@patch("time.sleep")  # Patch sleep to speed up test
def test_simulated_radio_interface_server_mode(
    mock_sleep: MagicMock,
    mock_socket: MagicMock,
) -> None:
    """Test SimulatedRadioInterface in server mode binds and listens."""
    mock_sock_instance = mock_socket.return_value
    interface = SimulatedRadioInterface(
        host="localhost",
        port=50000,
        server_mode=True,
        timeout=2.0,
    )

    # Simulate connection sequence
    mock_sock_instance.accept.side_effect = [
        BlockingIOError(),  # First call blocks
        (mock_sock_instance, ("clienthost", 9999)),  # Second call succeeds
    ]

    interface.connect()  # Should succeed after retry

    mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
    mock_sock_instance.bind.assert_called_once_with(("localhost", 50000))
    mock_sock_instance.listen.assert_called_once_with(1)
    mock_sock_instance.setblocking.assert_called_once_with(False)  # noqa: FBT003
    assert mock_sock_instance.settimeout.call_args_list == [  # noqa: S101
        call(2.0),  # Read timeout after connection
    ]
    mock_sleep.assert_called_once_with(0.1)  # Verify sleep was called between retries

    interface.close()
    mock_sock_instance.close.assert_called()
