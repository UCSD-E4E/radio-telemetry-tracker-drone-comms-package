"""Data classes for user-facing packet data structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SyncRequestData:
    """Data container for synchronization request packets."""

    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class SyncResponseData:
    """Data container for synchronization response packets."""

    success: bool
    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class ConfigRequestData:
    """Data container for configuration request packets."""

    gain: float
    sampling_rate: int
    center_frequency: int
    run_num: int
    enable_test_data: bool
    ping_width_ms: int
    ping_min_snr: int
    ping_max_len_mult: float
    ping_min_len_mult: float
    target_frequencies: list[int]
    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class ConfigResponseData:
    """Data container for configuration response packets."""

    success: bool
    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class GPSData:
    """Data container for GPS location packets."""

    easting: float
    northing: float
    altitude: float
    heading: float
    epsg_code: int
    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class PingData:
    """Data container for radio ping detection packets."""

    frequency: int
    amplitude: float
    easting: float
    northing: float
    altitude: float
    epsg_code: int
    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class LocEstData:
    """Data container for location estimation packets."""

    frequency: int
    easting: float
    northing: float
    epsg_code: int
    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class StartRequestData:
    """Data container for start request packets."""

    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class StartResponseData:
    """Data container for start response packets."""

    success: bool
    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class StopRequestData:
    """Data container for stop request packets."""

    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class StopResponseData:
    """Data container for stop response packets."""

    success: bool
    packet_id: int | None = None
    timestamp: int | None = None


@dataclass
class ErrorData:
    """Data container for error packets."""

    packet_id: int | None = None
    timestamp: int | None = None
