"""Unit tests for the protobuf compiler module."""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from radio_telemetry_tracker_drone_comms_package.proto.compiler import (
    ensure_proto_compiled,
)


def test_ensure_proto_compiled_success(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test that ensure_proto_compiled() calls protoc.main with success."""
    # Mock the Path used in compiler.py so it points to tmp_path
    mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.Path",
        return_value=tmp_path,
    )
    # Simulate a 'packets.proto' file existing
    (tmp_path / "packets.proto").write_text('syntax = "proto3";')

    mock_protoc_main = mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.protoc.main",
        return_value=0,
    )
    mock_logger = mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.logger",
        autospec=True,
    )

    ensure_proto_compiled()

    mock_protoc_main.assert_called_once()
    mock_logger.info.assert_called_once_with("Successfully compiled protobuf file")


def test_ensure_proto_compiled_nonzero_exit(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test that ensure_proto_compiled() raises RuntimeError if protoc.main returns non-zero."""
    mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.Path",
        return_value=tmp_path,
    )
    (tmp_path / "packets.proto").write_text('syntax = "proto3";')

    mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.protoc.main",
        return_value=1,
    )
    mock_logger = mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.logger",
        autospec=True,
    )

    with pytest.raises(RuntimeError) as exc_info:
        ensure_proto_compiled()

    assert "protoc returned non-zero status: 1" in str(exc_info.value)  # noqa: S101
    mock_logger.error.assert_any_call("protoc returned non-zero status: 1")


def test_ensure_proto_compiled_oserror(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test that ensure_proto_compiled() raises RuntimeError if protoc.main raises OSError."""
    mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.Path",
        return_value=tmp_path,
    )
    (tmp_path / "packets.proto").write_text('syntax = "proto3";')

    mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.protoc.main",
        side_effect=OSError("protoc not found"),
    )
    mock_logger = mocker.patch(
        "radio_telemetry_tracker_drone_comms_package.proto.compiler.logger",
        autospec=True,
    )

    with pytest.raises(RuntimeError) as exc_info:
        ensure_proto_compiled()

    assert "Failed to compile protobuf: protoc not found" in str(exc_info.value)  # noqa: S101
    mock_logger.error.assert_any_call(
        "Make sure grpcio-tools is installed:\npoetry add grpcio-tools",
    )
    mock_logger.error.assert_any_call("Failed to compile protobuf: protoc not found")
