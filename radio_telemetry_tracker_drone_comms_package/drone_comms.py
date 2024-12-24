"""High-level DroneComms class for user-facing interaction with radio telemetry packet communication."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, TypeVar

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
from radio_telemetry_tracker_drone_comms_package.interfaces import (
    SerialRadioInterface,
    SimulatedRadioInterface,
)
from radio_telemetry_tracker_drone_comms_package.proto import (
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
from radio_telemetry_tracker_drone_comms_package.transceiver import (
    PacketManager,
    _current_timestamp_us,
)

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class RadioConfig:
    """Configuration for radio interface."""

    interface_type: str = "serial"
    port: str | None = None
    baudrate: int = 56700
    host: str = "localhost"
    tcp_port: int = 50000
    server_mode: bool = False


class DroneComms(PacketManager):
    """Manages radio telemetry packet communication between drone and base station."""

    def __init__(
        self,
        radio_config: RadioConfig = None,
        ack_timeout: float = 2.0,
        max_retries: int = 5,
        on_ack_callback: Callable[[RadioPacket], None] | None = None,
    ) -> None:
        """Initialize DroneComms instance.

        Args:
            radio_config: Configuration for radio interface
            ack_timeout: Timeout in seconds for acknowledgment packets
            max_retries: Maximum number of packet retransmission attempts
            on_ack_callback: Optional callback function when acknowledgment is received
        """
        if radio_config is None:
            msg = "Radio config is required"
            raise ValueError(msg)

        if radio_config.interface_type == "serial":
            if radio_config.port is None:
                msg = "Serial port must be specified for serial interface"
                raise ValueError(msg)
            radio_interface = SerialRadioInterface(
                port=radio_config.port,
                baudrate=radio_config.baudrate,
                timeout=ack_timeout,
            )
        elif radio_config.interface_type == "simulated":
            radio_interface = SimulatedRadioInterface(
                host=radio_config.host,
                port=radio_config.tcp_port,
                server_mode=radio_config.server_mode,
                timeout=ack_timeout,
            )
        else:
            msg = f"Invalid interface type: {radio_config.interface_type}"
            raise ValueError(msg)

        super().__init__(
            radio_interface=radio_interface,
            ack_timeout=ack_timeout,
            max_retries=max_retries,
            on_ack_timeout=on_ack_callback,
        )

        # Each entry: "proto_field_name": (extractor_function, handler_function)
        self._packet_handlers = {
            "syn_rqt": (self._extract_sync_request, self._handle_sync_request),
            "syn_rsp": (self._extract_sync_response, self._handle_sync_response),
            "cfg_rqt": (self._extract_config_request, self._handle_config_request),
            "cfg_rsp": (self._extract_config_response, self._handle_config_response),
            "gps_pkt": (self._extract_gps_data, self._handle_gps_data),
            "ping_pkt": (self._extract_ping_data, self._handle_ping_data),
            "loc_pkt": (self._extract_loc_est_data, self._handle_loc_est_data),
            "str_rqt": (self._extract_start_request, self._handle_start_request),
            "str_rsp": (self._extract_start_response, self._handle_start_response),
            "stp_rqt": (self._extract_stop_request, self._handle_stop_request),
            "stp_rsp": (self._extract_stop_response, self._handle_stop_response),
            "err_pkt": (self._extract_error, self._handle_error),
        }

        # Handlers for different packet types: [ (callback, once), ... ]
        self._sync_request_handlers: list[
            tuple[Callable[[SyncRequestData], None], bool]
        ] = []
        self._sync_response_handlers: list[
            tuple[Callable[[SyncResponseData], None], bool]
        ] = []
        self._config_request_handlers: list[
            tuple[Callable[[ConfigRequestData], None], bool]
        ] = []
        self._config_response_handlers: list[
            tuple[Callable[[ConfigResponseData], None], bool]
        ] = []
        self._gps_handlers: list[tuple[Callable[[GPSData], None], bool]] = []
        self._ping_handlers: list[tuple[Callable[[PingData], None], bool]] = []
        self._loc_est_handlers: list[tuple[Callable[[LocEstData], None], bool]] = []
        self._start_request_handlers: list[
            tuple[Callable[[StartRequestData], None], bool]
        ] = []
        self._start_response_handlers: list[
            tuple[Callable[[StartResponseData], None], bool]
        ] = []
        self._stop_request_handlers: list[
            tuple[Callable[[StopRequestData], None], bool]
        ] = []
        self._stop_response_handlers: list[
            tuple[Callable[[StopResponseData], None], bool]
        ] = []
        self._error_handlers: list[tuple[Callable[[ErrorData], None], bool]] = []

    def on_user_packet_received(self, packet: RadioPacket) -> None:
        """Handle received user packets by delegating to typed handlers. Overridden from PacketManager."""
        field = packet.WhichOneof("msg")
        handler_entry = self._packet_handlers.get(field)
        if not handler_entry:
            logger.debug("Received an unhandled packet type: %s", field)
            return

        extractor, handler = handler_entry
        data_object = extractor(getattr(packet, field))
        handler(data_object)

    # --------------------------------------------------------------------------
    # Handler registration/unregistration (public)
    # --------------------------------------------------------------------------

    def register_sync_request_handler(
        self,
        callback: Callable[[SyncRequestData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for sync request packets.

        Args:
            callback: Function to call when sync request is received
            once: If True, handler is removed after first invocation
        """
        self._sync_request_handlers.append((callback, once))

    def unregister_sync_request_handler(
        self,
        callback: Callable[[SyncRequestData], None],
    ) -> bool:
        """Unregister a previously registered sync request handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._sync_request_handlers:
            if cb == callback:
                self._sync_request_handlers.remove((cb, once))
                return True
        return False

    def register_sync_response_handler(
        self,
        callback: Callable[[SyncResponseData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for sync response packets.

        Args:
            callback: Function to call when sync response is received
            once: If True, handler is removed after first invocation
        """
        self._sync_response_handlers.append((callback, once))

    def unregister_sync_response_handler(
        self,
        callback: Callable[[SyncResponseData], None],
    ) -> bool:
        """Unregister a previously registered sync response handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._sync_response_handlers:
            if cb == callback:
                self._sync_response_handlers.remove((cb, once))
                return True
        return False

    def register_config_request_handler(
        self,
        callback: Callable[[ConfigRequestData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for config request packets.

        Args:
            callback: Function to call when config request is received
            once: If True, handler is removed after first invocation
        """
        self._config_request_handlers.append((callback, once))

    def unregister_config_request_handler(
        self,
        callback: Callable[[ConfigRequestData], None],
    ) -> bool:
        """Unregister a previously registered config request handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._config_request_handlers:
            if cb == callback:
                self._config_request_handlers.remove((cb, once))
                return True
        return False

    def register_config_response_handler(
        self,
        callback: Callable[[ConfigResponseData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for config response packets.

        Args:
            callback: Function to call when config response is received
            once: If True, handler is removed after first invocation
        """
        self._config_response_handlers.append((callback, once))

    def unregister_config_response_handler(
        self,
        callback: Callable[[ConfigResponseData], None],
    ) -> bool:
        """Unregister a previously registered config response handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._config_response_handlers:
            if cb == callback:
                self._config_response_handlers.remove((cb, once))
                return True
        return False

    def register_gps_handler(
        self,
        callback: Callable[[GPSData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for GPS data packets.

        Args:
            callback: Function to call when GPS data is received
            once: If True, handler is removed after first invocation
        """
        self._gps_handlers.append((callback, once))

    def unregister_gps_handler(self, callback: Callable[[GPSData], None]) -> bool:
        """Unregister a previously registered GPS data handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._gps_handlers:
            if cb == callback:
                self._gps_handlers.remove((cb, once))
                return True
        return False

    def register_ping_handler(
        self,
        callback: Callable[[PingData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for ping data packets.

        Args:
            callback: Function to call when ping data is received
            once: If True, handler is removed after first invocation
        """
        self._ping_handlers.append((callback, once))

    def unregister_ping_handler(self, callback: Callable[[PingData], None]) -> bool:
        """Unregister a previously registered ping data handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._ping_handlers:
            if cb == callback:
                self._ping_handlers.remove((cb, once))
                return True
        return False

    def register_loc_est_handler(
        self,
        callback: Callable[[LocEstData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for location estimation data packets.

        Args:
            callback: Function to call when location estimation data is received
            once: If True, handler is removed after first invocation
        """
        self._loc_est_handlers.append((callback, once))

    def unregister_loc_est_handler(
        self,
        callback: Callable[[LocEstData], None],
    ) -> bool:
        """Unregister a previously registered location estimation data handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._loc_est_handlers:
            if cb == callback:
                self._loc_est_handlers.remove((cb, once))
                return True
        return False

    def register_start_request_handler(
        self,
        callback: Callable[[StartRequestData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for start request packets.

        Args:
            callback: Function to call when start request is received
            once: If True, handler is removed after first invocation
        """
        self._start_request_handlers.append((callback, once))

    def unregister_start_request_handler(
        self,
        callback: Callable[[StartRequestData], None],
    ) -> bool:
        """Unregister a previously registered start request handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._start_request_handlers:
            if cb == callback:
                self._start_request_handlers.remove((cb, once))
                return True
        return False

    def register_start_response_handler(
        self,
        callback: Callable[[StartResponseData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for start response packets.

        Args:
            callback: Function to call when start response is received
            once: If True, handler is removed after first invocation
        """
        self._start_response_handlers.append((callback, once))

    def unregister_start_response_handler(
        self,
        callback: Callable[[StartResponseData], None],
    ) -> bool:
        """Unregister a previously registered start response handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._start_response_handlers:
            if cb == callback:
                self._start_response_handlers.remove((cb, once))
                return True
        return False

    def register_stop_request_handler(
        self,
        callback: Callable[[StopRequestData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for stop request packets.

        Args:
            callback: Function to call when stop request is received
            once: If True, handler is removed after first invocation
        """
        self._stop_request_handlers.append((callback, once))

    def unregister_stop_request_handler(
        self,
        callback: Callable[[StopRequestData], None],
    ) -> bool:
        """Unregister a previously registered stop request handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._stop_request_handlers:
            if cb == callback:
                self._stop_request_handlers.remove((cb, once))
                return True
        return False

    def register_stop_response_handler(
        self,
        callback: Callable[[StopResponseData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for stop response packets.

        Args:
            callback: Function to call when stop response is received
            once: If True, handler is removed after first invocation
        """
        self._stop_response_handlers.append((callback, once))

    def unregister_stop_response_handler(
        self,
        callback: Callable[[StopResponseData], None],
    ) -> bool:
        """Unregister a previously registered stop response handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._stop_response_handlers:
            if cb == callback:
                self._stop_response_handlers.remove((cb, once))
                return True
        return False

    def register_error_handler(
        self,
        callback: Callable[[ErrorData], None],
        *,
        once: bool = False,
    ) -> None:
        """Register a handler for error packets.

        Args:
            callback: Function to call when error packet is received
            once: If True, handler is removed after first invocation
        """
        self._error_handlers.append((callback, once))

    def unregister_error_handler(self, callback: Callable[[ErrorData], None]) -> bool:
        """Unregister a previously registered error handler.

        Args:
            callback: The handler function to remove

        Returns:
            bool: True if handler was found and removed, False otherwise
        """
        for cb, once in self._error_handlers:
            if cb == callback:
                self._error_handlers.remove((cb, once))
                return True
        return False

    # --------------------------------------------------------------------------
    # Public send methods
    # --------------------------------------------------------------------------

    def send_sync_request(self, _: SyncRequestData) -> tuple[int, bool, int]:
        """Send a sync request packet.

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.syn_rqt.base.packet_id = self.generate_packet_id()
        packet.syn_rqt.base.need_ack = True
        packet.syn_rqt.base.timestamp = _current_timestamp_us()
        self.enqueue_packet(packet)
        return (
            packet.syn_rqt.base.packet_id,
            packet.syn_rqt.base.need_ack,
            packet.syn_rqt.base.timestamp,
        )

    def send_sync_response(self, data: SyncResponseData) -> tuple[int, bool, int]:
        """Send a sync response packet.

        Args:
            data: Sync response data to send

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.syn_rsp.base.packet_id = self.generate_packet_id()
        packet.syn_rsp.base.need_ack = False
        packet.syn_rsp.base.timestamp = _current_timestamp_us()
        packet.syn_rsp.success = data.success
        self.enqueue_packet(packet)
        return (
            packet.syn_rsp.base.packet_id,
            packet.syn_rsp.base.need_ack,
            packet.syn_rsp.base.timestamp,
        )

    def send_config_request(self, data: ConfigRequestData) -> tuple[int, bool, int]:
        """Send a config request packet.

        Args:
            data: Config request data to send

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.cfg_rqt.base.packet_id = self.generate_packet_id()
        packet.cfg_rqt.base.need_ack = True
        packet.cfg_rqt.base.timestamp = _current_timestamp_us()
        packet.cfg_rqt.gain = data.gain
        packet.cfg_rqt.sampling_rate = data.sampling_rate
        packet.cfg_rqt.center_frequency = data.center_frequency
        packet.cfg_rqt.run_num = data.run_num
        packet.cfg_rqt.enable_test_data = data.enable_test_data
        packet.cfg_rqt.ping_width_ms = data.ping_width_ms
        packet.cfg_rqt.ping_min_snr = data.ping_min_snr
        packet.cfg_rqt.ping_max_len_mult = data.ping_max_len_mult
        packet.cfg_rqt.ping_min_len_mult = data.ping_min_len_mult
        packet.cfg_rqt.target_frequencies.extend(data.target_frequencies)
        self.enqueue_packet(packet)
        return (
            packet.cfg_rqt.base.packet_id,
            packet.cfg_rqt.base.need_ack,
            packet.cfg_rqt.base.timestamp,
        )

    def send_config_response(self, data: ConfigResponseData) -> tuple[int, bool, int]:
        """Send a config response packet.

        Args:
            data: Config response data to send

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.cfg_rsp.base.packet_id = self.generate_packet_id()
        packet.cfg_rsp.base.need_ack = False
        packet.cfg_rsp.base.timestamp = _current_timestamp_us()
        packet.cfg_rsp.success = data.success
        self.enqueue_packet(packet)
        return (
            packet.cfg_rsp.base.packet_id,
            packet.cfg_rsp.base.need_ack,
            packet.cfg_rsp.base.timestamp,
        )

    def send_gps_data(self, data: GPSData) -> tuple[int, bool, int]:
        """Send a GPS data packet.

        Args:
            data: GPS data to send

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.gps_pkt.base.packet_id = self.generate_packet_id()
        packet.gps_pkt.base.need_ack = False
        packet.gps_pkt.base.timestamp = _current_timestamp_us()
        packet.gps_pkt.easting = data.easting
        packet.gps_pkt.northing = data.northing
        packet.gps_pkt.altitude = data.altitude
        packet.gps_pkt.heading = data.heading
        packet.gps_pkt.epsg_code = data.epsg_code
        self.enqueue_packet(packet)
        return (
            packet.gps_pkt.base.packet_id,
            packet.gps_pkt.base.need_ack,
            packet.gps_pkt.base.timestamp,
        )

    def send_ping_data(self, data: PingData) -> tuple[int, bool, int]:
        """Send a ping data packet.

        Args:
            data: Ping data to send

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.ping_pkt.base.packet_id = self.generate_packet_id()
        packet.ping_pkt.base.need_ack = False
        packet.ping_pkt.base.timestamp = _current_timestamp_us()
        packet.ping_pkt.frequency = data.frequency
        packet.ping_pkt.amplitude = data.amplitude
        packet.ping_pkt.easting = data.easting
        packet.ping_pkt.northing = data.northing
        packet.ping_pkt.altitude = data.altitude
        packet.ping_pkt.epsg_code = data.epsg_code
        self.enqueue_packet(packet)
        return (
            packet.ping_pkt.base.packet_id,
            packet.ping_pkt.base.need_ack,
            packet.ping_pkt.base.timestamp,
        )

    def send_loc_est_data(self, data: LocEstData) -> tuple[int, bool, int]:
        """Send a location estimation data packet.

        Args:
            data: Location estimation data to send

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.loc_pkt.base.packet_id = self.generate_packet_id()
        packet.loc_pkt.base.need_ack = False
        packet.loc_pkt.base.timestamp = _current_timestamp_us()
        packet.loc_pkt.frequency = data.frequency
        packet.loc_pkt.easting = data.easting
        packet.loc_pkt.northing = data.northing
        packet.loc_pkt.epsg_code = data.epsg_code
        self.enqueue_packet(packet)
        return (
            packet.loc_pkt.base.packet_id,
            packet.loc_pkt.base.need_ack,
            packet.loc_pkt.base.timestamp,
        )

    def send_start_request(self, _: StartRequestData) -> tuple[int, bool, int]:
        """Send a start request packet.

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.str_rqt.base.packet_id = self.generate_packet_id()
        packet.str_rqt.base.need_ack = True
        packet.str_rqt.base.timestamp = _current_timestamp_us()
        self.enqueue_packet(packet)
        return (
            packet.str_rqt.base.packet_id,
            packet.str_rqt.base.need_ack,
            packet.str_rqt.base.timestamp,
        )

    def send_start_response(self, data: StartResponseData) -> tuple[int, bool, int]:
        """Send a start response packet.

        Args:
            data: Start response data to send

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.str_rsp.base.packet_id = self.generate_packet_id()
        packet.str_rsp.base.need_ack = False
        packet.str_rsp.base.timestamp = _current_timestamp_us()
        packet.str_rsp.success = data.success
        self.enqueue_packet(packet)
        return (
            packet.str_rsp.base.packet_id,
            packet.str_rsp.base.need_ack,
            packet.str_rsp.base.timestamp,
        )

    def send_stop_request(self, _: StopRequestData) -> tuple[int, bool, int]:
        """Send a stop request packet.

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.stp_rqt.base.packet_id = self.generate_packet_id()
        packet.stp_rqt.base.need_ack = True
        packet.stp_rqt.base.timestamp = _current_timestamp_us()
        self.enqueue_packet(packet)
        return (
            packet.stp_rqt.base.packet_id,
            packet.stp_rqt.base.need_ack,
            packet.stp_rqt.base.timestamp,
        )

    def send_stop_response(self, data: StopResponseData) -> tuple[int, bool, int]:
        """Send a stop response packet.

        Args:
            data: Stop response data to send

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.stp_rsp.base.packet_id = self.generate_packet_id()
        packet.stp_rsp.base.need_ack = False
        packet.stp_rsp.base.timestamp = _current_timestamp_us()
        packet.stp_rsp.success = data.success
        self.enqueue_packet(packet)
        return (
            packet.stp_rsp.base.packet_id,
            packet.stp_rsp.base.need_ack,
            packet.stp_rsp.base.timestamp,
        )

    def send_error(self, _: ErrorData) -> tuple[int, bool, int]:
        """Send an error packet.

        Returns:
            tuple: (packet_id, need_ack, timestamp)
        """
        packet = RadioPacket()
        packet.err_pkt.base.packet_id = self.generate_packet_id()
        packet.err_pkt.base.need_ack = False
        packet.err_pkt.base.timestamp = _current_timestamp_us()
        self.enqueue_packet(packet)
        return (
            packet.err_pkt.base.packet_id,
            packet.err_pkt.base.need_ack,
            packet.err_pkt.base.timestamp,
        )

    # --------------------------------------------------------------------------
    # Private extractor methods
    # --------------------------------------------------------------------------

    def _extract_sync_request(self, packet: SyncRequestPacket) -> SyncRequestData:
        return SyncRequestData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
        )

    def _extract_sync_response(self, packet: SyncResponsePacket) -> SyncResponseData:
        return SyncResponseData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
            success=packet.success,
        )

    def _extract_config_request(self, packet: ConfigRequestPacket) -> ConfigRequestData:
        return ConfigRequestData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
            gain=packet.gain,
            sampling_rate=packet.sampling_rate,
            center_frequency=packet.center_frequency,
            run_num=packet.run_num,
            enable_test_data=packet.enable_test_data,
            ping_width_ms=packet.ping_width_ms,
            ping_min_snr=packet.ping_min_snr,
            ping_max_len_mult=packet.ping_max_len_mult,
            ping_min_len_mult=packet.ping_min_len_mult,
            target_frequencies=list(packet.target_frequencies),
        )

    def _extract_config_response(
        self,
        packet: ConfigResponsePacket,
    ) -> ConfigResponseData:
        return ConfigResponseData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
            success=packet.success,
        )

    def _extract_gps_data(self, packet: GPSPacket) -> GPSData:
        return GPSData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
            easting=packet.easting,
            northing=packet.northing,
            altitude=packet.altitude,
            heading=packet.heading,
            epsg_code=packet.epsg_code,
        )

    def _extract_ping_data(self, packet: PingPacket) -> PingData:
        return PingData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
            frequency=packet.frequency,
            amplitude=packet.amplitude,
            easting=packet.easting,
            northing=packet.northing,
            altitude=packet.altitude,
            epsg_code=packet.epsg_code,
        )

    def _extract_loc_est_data(self, packet: LocEstPacket) -> LocEstData:
        return LocEstData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
            frequency=packet.frequency,
            easting=packet.easting,
            northing=packet.northing,
            epsg_code=packet.epsg_code,
        )

    def _extract_start_request(self, packet: StartRequestPacket) -> StartRequestData:
        return StartRequestData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
        )

    def _extract_start_response(self, packet: StartResponsePacket) -> StartResponseData:
        return StartResponseData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
            success=packet.success,
        )

    def _extract_stop_request(self, packet: StopRequestPacket) -> StopRequestData:
        return StopRequestData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
        )

    def _extract_stop_response(self, packet: StopResponsePacket) -> StopResponseData:
        return StopResponseData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
            success=packet.success,
        )

    def _extract_error(self, packet: ErrorPacket) -> ErrorData:
        return ErrorData(
            packet_id=packet.base.packet_id,
            timestamp=packet.base.timestamp,
        )

    # --------------------------------------------------------------------------
    # Private handler methods that call user-registered callbacks
    # --------------------------------------------------------------------------

    def _handle_sync_request(self, data: SyncRequestData) -> None:
        self._invoke_handlers(self._sync_request_handlers, data)

    def _handle_sync_response(self, data: SyncResponseData) -> None:
        self._invoke_handlers(self._sync_response_handlers, data)

    def _handle_config_request(self, data: ConfigRequestData) -> None:
        self._invoke_handlers(self._config_request_handlers, data)

    def _handle_config_response(self, data: ConfigResponseData) -> None:
        self._invoke_handlers(self._config_response_handlers, data)

    def _handle_gps_data(self, data: GPSData) -> None:
        self._invoke_handlers(self._gps_handlers, data)

    def _handle_ping_data(self, data: PingData) -> None:
        self._invoke_handlers(self._ping_handlers, data)

    def _handle_loc_est_data(self, data: LocEstData) -> None:
        self._invoke_handlers(self._loc_est_handlers, data)

    def _handle_start_request(self, data: StartRequestData) -> None:
        self._invoke_handlers(self._start_request_handlers, data)

    def _handle_start_response(self, data: StartResponseData) -> None:
        self._invoke_handlers(self._start_response_handlers, data)

    def _handle_stop_request(self, data: StopRequestData) -> None:
        self._invoke_handlers(self._stop_request_handlers, data)

    def _handle_stop_response(self, data: StopResponseData) -> None:
        self._invoke_handlers(self._stop_response_handlers, data)

    def _handle_error(self, data: ErrorData) -> None:
        self._invoke_handlers(self._error_handlers, data)

    @staticmethod
    def _invoke_handlers(
        handlers_list: list[tuple[Callable[[T], None], bool]],
        data: T,
    ) -> None:
        to_remove = []
        for i, (callback, once) in enumerate(handlers_list):
            callback(data)
            if once:
                to_remove.append(i)
        for i in reversed(to_remove):
            handlers_list.pop(i)
