"""Unit tests for the data model classes used in radio telemetry packet handling."""

from typing import Any

import pytest

from radio_telemetry_tracker_drone_comms_package.data_models import (
    ConfigRequestData,
    ConfigResponseData,
    ErrorData,
    GPSData,
    LocEstData,
    PingData,
    StartRequestData,
    StartResponseData,
    StopRequestData,
    StopResponseData,
    SyncRequestData,
    SyncResponseData,
)

# Test constants
TEST_GAIN = 1.5
TEST_SAMPLING_RATE = 48000
TEST_TARGET_FREQUENCIES = [100, 200, 300]
TEST_SYNC_PACKET_ID = 123
TEST_SYNC_TIMESTAMP = 456789


def test_sync_request_data() -> None:
    """Test SyncRequestData initialization and attribute access."""
    data = SyncRequestData(packet_id=TEST_SYNC_PACKET_ID, timestamp=TEST_SYNC_TIMESTAMP)
    assert data.packet_id == TEST_SYNC_PACKET_ID  # noqa: S101
    assert data.timestamp == TEST_SYNC_TIMESTAMP  # noqa: S101


def test_config_request_data() -> None:
    """Test ConfigRequestData initialization with all parameters."""
    data = ConfigRequestData(
        packet_id=10,
        timestamp=999,
        gain=TEST_GAIN,
        sampling_rate=TEST_SAMPLING_RATE,
        center_frequency=150000,
        run_num=1,
        enable_test_data=True,
        ping_width_ms=10,
        ping_min_snr=5,
        ping_max_len_mult=2.5,
        ping_min_len_mult=1.2,
        target_frequencies=TEST_TARGET_FREQUENCIES,
    )
    assert data.gain == TEST_GAIN  # noqa: S101
    assert data.sampling_rate == TEST_SAMPLING_RATE  # noqa: S101
    assert data.target_frequencies == TEST_TARGET_FREQUENCIES  # noqa: S101


@pytest.mark.parametrize(
    ("klass", "kwargs"),
    [
        (SyncResponseData, {"success": True, "packet_id": 1, "timestamp": 1000}),
        (ConfigResponseData, {"success": False, "packet_id": 2, "timestamp": 2000}),
        (
            GPSData,
            {
                "packet_id": 3,
                "timestamp": 3000,
                "easting": 10.0,
                "northing": 20.0,
                "altitude": 100.0,
                "heading": 45.5,
                "epsg_code": 4326,
            },
        ),
        (
            PingData,
            {
                "packet_id": 4,
                "timestamp": 4000,
                "frequency": 120,
                "amplitude": 0.8,
                "easting": 123.4,
                "northing": 567.8,
                "altitude": 9.0,
                "epsg_code": 4326,
            },
        ),
        (
            LocEstData,
            {
                "packet_id": 5,
                "timestamp": 5000,
                "frequency": 180,
                "easting": 111.1,
                "northing": 222.2,
                "epsg_code": 4326,
            },
        ),
        (StartRequestData, {"packet_id": 6, "timestamp": 6000}),
        (StartResponseData, {"packet_id": 7, "timestamp": 7000, "success": True}),
        (StopRequestData, {"packet_id": 8, "timestamp": 8000}),
        (StopResponseData, {"packet_id": 9, "timestamp": 9000, "success": False}),
        (ErrorData, {"packet_id": 10, "timestamp": 10000}),
    ],
)
def test_data_classes(klass: type[Any], kwargs: dict[str, Any]) -> None:
    """Test initialization and attribute access for all data model classes."""
    instance = klass(**kwargs)
    for k, v in kwargs.items():
        assert getattr(instance, k) == v  # noqa: S101
