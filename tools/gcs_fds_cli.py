"""Command-line interface for testing drone communications."""

from __future__ import annotations

import argparse
import cmd
import logging
import sys
from typing import Callable

from radio_telemetry_tracker_drone_comms_package import (
    ConfigRequestData,
    ConfigResponseData,
    DroneComms,
    ErrorData,
    GPSData,
    LocEstData,
    PingData,
    RadioConfig,
    StartRequestData,
    StartResponseData,
    StopRequestData,
    StopResponseData,
    SyncRequestData,
    SyncResponseData,
)

logger = logging.getLogger(__name__)


class GCSFDSCLI(cmd.Cmd):
    """Interactive CLI for testing drone communications."""

    intro = "Welcome to the GCS/FDS CLI. Type help or ? to list commands.\n"
    prompt = "(gcs-fds) "

    def __init__(self, radio_config: RadioConfig) -> None:
        """Initialize the CLI with radio configuration.

        Args:
            radio_config: Configuration for the radio interface
        """
        super().__init__()
        self.drone_comms = None
        self.radio_config = radio_config
        self.started = False

        # Store callback references
        self.registered_callbacks = {}

        # Map packet types to their register/unregister method names
        self.packet_type_map = {
            "sync": (
                "register_sync_request_handler",
                "unregister_sync_request_handler",
            ),
            "sync_response": (
                "register_sync_response_handler",
                "unregister_sync_response_handler",
            ),
            "config": (
                "register_config_request_handler",
                "unregister_config_request_handler",
            ),
            "config_response": (
                "register_config_response_handler",
                "unregister_config_response_handler",
            ),
            "gps": ("register_gps_handler", "unregister_gps_handler"),
            "ping": ("register_ping_handler", "unregister_ping_handler"),
            "loc": ("register_loc_est_handler", "unregister_loc_est_handler"),
            "start": (
                "register_start_request_handler",
                "unregister_start_request_handler",
            ),
            "start_response": (
                "register_start_response_handler",
                "unregister_start_response_handler",
            ),
            "stop": (
                "register_stop_request_handler",
                "unregister_stop_request_handler",
            ),
            "stop_response": (
                "register_stop_response_handler",
                "unregister_stop_response_handler",
            ),
            "error": ("register_error_handler", "unregister_error_handler"),
        }

    def do_start(self, arg: str) -> None:  # noqa: ARG002
        """Start the drone communications.

        Args:
            arg: Command argument (unused)
        """
        if self.started:
            logger.info("Already started.")
            return

        self.drone_comms = DroneComms(radio_config=self.radio_config)
        self.drone_comms.start()
        self.started = True
        logger.info("Started drone communications.")

    def do_stop(self, arg: str) -> None:  # noqa: ARG002
        """Stop the drone communications.

        Args:
            arg: Command argument (unused)
        """
        if not self.started:
            logger.info("Not started.")
            return

        self.drone_comms.stop()
        self.started = False
        logger.info("Stopped drone communications.")

    def do_register(self, arg: str) -> None:
        """Register a callback for a specific packet type.

        Args:
            arg: Command argument
        """
        parts = arg.split()
        if not parts:
            logger.info("Usage: register <packet_type> [once]")
            return
        pkt_type = parts[0].lower()
        once = (len(parts) > 1) and (parts[1].lower() == "once")

        if pkt_type not in self.packet_type_map:
            logger.info("Unknown packet type: %s", pkt_type)
            return

        register_method_name, _ = self.packet_type_map[pkt_type]
        register_method = getattr(self.drone_comms, register_method_name)

        # Create and store callback reference
        callback_func = self.make_print_callback(pkt_type)
        if pkt_type not in self.registered_callbacks:
            self.registered_callbacks[pkt_type] = []
        self.registered_callbacks[pkt_type].append(callback_func)

        register_method(callback_func, once=once)
        mode_str = "ONCE" if once else "ALWAYS"
        logger.info("Registered print callback for '%s' (%s).", pkt_type, mode_str)

    def do_unregister(self, arg: str) -> None:
        """Unregister a callback for a specific packet type.

        Args:
            arg: Command argument
        """
        pkt_type = arg.strip().lower()
        if pkt_type not in self.packet_type_map:
            logger.info("Unknown packet type: %s", pkt_type)
            return

        if (
            pkt_type not in self.registered_callbacks
            or not self.registered_callbacks[pkt_type]
        ):
            logger.info("No callbacks registered for '%s'.", pkt_type)
            return

        _, unregister_method_name = self.packet_type_map[pkt_type]
        unregister_method = getattr(self.drone_comms, unregister_method_name)

        # Unregister all callbacks for this packet type
        success = False
        for callback in self.registered_callbacks[pkt_type]:
            if unregister_method(callback):
                success = True

        if success:
            self.registered_callbacks[pkt_type].clear()
            logger.info("Unregistered callbacks for '%s'.", pkt_type)
        else:
            logger.info("Failed to unregister callbacks (unexpected error).")

    def do_send_sync_request(self, arg: str) -> None:  # noqa: ARG002
        """Send a sync request packet.

        Args:
            arg: Command argument (unused)
        """
        pid, ack, ts = self.drone_comms.send_sync_request(SyncRequestData())
        logger.info(
            "Sent SyncRequest (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_sync_response(self, arg: str) -> None:
        """Send sync response packet.

        Args:
            arg: Command argument
        """
        parts = arg.split()
        success = True
        if parts and parts[0].lower() in ("false", "0", "no"):
            success = False

        data = SyncResponseData(success=success)
        pid, ack, ts = self.drone_comms.send_sync_response(data)
        logger.info(
            "Sent SyncResponse (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def _get_default_config(self) -> ConfigRequestData:
        """Get default configuration values.

        Returns:
            Default ConfigRequestData
        """
        return ConfigRequestData(
            gain=50.0,
            sampling_rate=2_000_000,
            center_frequency=150_000_000,
            run_num=1,
            enable_test_data=False,
            ping_width_ms=20,
            ping_min_snr=10,
            ping_max_len_mult=1.5,
            ping_min_len_mult=0.5,
            target_frequencies=[150_000_000],
        )

    def _parse_config_request_args(self, args: list[str]) -> ConfigRequestData | None:
        """Parse arguments for config request.

        Args:
            args: List of argument strings

        Returns:
            Parsed ConfigRequestData or None if parsing failed
        """
        min_args_for_frequencies = 10
        data = self._get_default_config()

        try:
            parsers = [
                (1, lambda x: setattr(data, "gain", float(x))),
                (2, lambda x: setattr(data, "sampling_rate", int(x))),
                (3, lambda x: setattr(data, "center_frequency", int(x))),
                (4, lambda x: setattr(data, "run_num", int(x))),
                (
                    5,
                    lambda x: setattr(
                        data,
                        "enable_test_data",
                        x.lower() in ("true", "1", "yes"),
                    ),
                ),
                (6, lambda x: setattr(data, "ping_width_ms", int(x))),
                (7, lambda x: setattr(data, "ping_min_snr", int(x))),
                (8, lambda x: setattr(data, "ping_max_len_mult", float(x))),
                (9, lambda x: setattr(data, "ping_min_len_mult", float(x))),
            ]

            for idx, parser in parsers:
                if len(args) >= idx:
                    parser(args[idx - 1])

            if len(args) >= min_args_for_frequencies:
                data.target_frequencies = [int(f) for f in args[9:]]
        except ValueError:
            logger.exception("Invalid argument format: %s")
            return None
        return data

    def do_send_config_request(self, arg: str) -> None:
        """Send config request packet.

        Args:
            arg: Command argument in format:
                [gain] [sampling_rate] [center_freq] [run_num] [test_data]
                [ping_width] [ping_snr] [max_len_mult] [min_len_mult] [target_freqs...]
        """
        parts = arg.split()
        data = (
            self._parse_config_request_args(parts)
            if parts
            else ConfigRequestData(
                gain=50.0,
                sampling_rate=2_000_000,
                center_frequency=150_000_000,
                run_num=1,
                enable_test_data=False,
                ping_width_ms=20,
                ping_min_snr=10,
                ping_max_len_mult=1.5,
                ping_min_len_mult=0.5,
                target_frequencies=[150_000_000],
            )
        )

        if data is None:
            return

        pid, ack, ts = self.drone_comms.send_config_request(data)
        logger.info(
            "Sent ConfigRequest (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_config_response(self, arg: str) -> None:
        """Send config response packet.

        Args:
            arg: Command argument
        """
        parts = arg.split()
        success = True
        if parts and parts[0].lower() in ("false", "0", "no"):
            success = False

        data = ConfigResponseData(success=success)
        pid, ack, ts = self.drone_comms.send_config_response(data)
        logger.info(
            "Sent ConfigResponse (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_gps(self, arg: str) -> None:
        """Send GPS packet.

        Args:
            arg: Command argument in format: [easting] [northing] [altitude] [heading] [epsg_code]
        """
        # Default values
        data = GPSData(
            easting=500000.0,
            northing=4000000.0,
            altitude=100.0,
            heading=45.0,
            epsg_code=32610,
        )

        # Parse arguments if provided
        parts = arg.split()
        if parts:
            try:
                min_args = {
                    "easting": 1,
                    "northing": 2,
                    "altitude": 3,
                    "heading": 4,
                    "epsg_code": 5,
                }
                if len(parts) >= min_args["easting"]:
                    data.easting = float(parts[0])
                if len(parts) >= min_args["northing"]:
                    data.northing = float(parts[1])
                if len(parts) >= min_args["altitude"]:
                    data.altitude = float(parts[2])
                if len(parts) >= min_args["heading"]:
                    data.heading = float(parts[3])
                if len(parts) >= min_args["epsg_code"]:
                    data.epsg_code = int(parts[4])
            except ValueError:
                logger.exception("Invalid argument format: %s")
                return

        pid, ack, ts = self.drone_comms.send_gps(data)
        logger.info(
            "Sent GPS (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_ping(self, arg: str) -> None:
        """Send ping packet.

        Args:
            arg: Command argument in format: [frequency] [amplitude] [easting] [northing] [altitude] [epsg_code]
        """
        # Default values
        data = PingData(
            frequency=150_000_000,
            amplitude=1.0,
            easting=500000.0,
            northing=4000000.0,
            altitude=100.0,
            epsg_code=32610,
        )

        # Parse arguments if provided
        parts = arg.split()
        if parts:
            try:
                min_args = {
                    "frequency": 1,
                    "amplitude": 2,
                    "easting": 3,
                    "northing": 4,
                    "altitude": 5,
                    "epsg_code": 6,
                }
                if len(parts) >= min_args["frequency"]:
                    data.frequency = int(parts[0])
                if len(parts) >= min_args["amplitude"]:
                    data.amplitude = float(parts[1])
                if len(parts) >= min_args["easting"]:
                    data.easting = float(parts[2])
                if len(parts) >= min_args["northing"]:
                    data.northing = float(parts[3])
                if len(parts) >= min_args["altitude"]:
                    data.altitude = float(parts[4])
                if len(parts) >= min_args["epsg_code"]:
                    data.epsg_code = int(parts[5])
            except ValueError:
                logger.exception("Invalid argument format: %s")
                return

        pid, ack, ts = self.drone_comms.send_ping(data)
        logger.info(
            "Sent Ping (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_loc_est(self, arg: str) -> None:
        """Send location estimate packet.

        Args:
            arg: Command argument in format: [frequency] [easting] [northing] [epsg_code]
        """
        # Default values
        data = LocEstData(
            frequency=150_000_000,
            easting=500000.0,
            northing=4000000.0,
            epsg_code=32610,
        )

        # Parse arguments if provided
        parts = arg.split()
        if parts:
            try:
                min_args = {
                    "frequency": 1,
                    "easting": 2,
                    "northing": 3,
                    "epsg_code": 4,
                }
                if len(parts) >= min_args["frequency"]:
                    data.frequency = int(parts[0])
                if len(parts) >= min_args["easting"]:
                    data.easting = float(parts[1])
                if len(parts) >= min_args["northing"]:
                    data.northing = float(parts[2])
                if len(parts) >= min_args["epsg_code"]:
                    data.epsg_code = int(parts[3])
            except ValueError:
                logger.exception("Invalid argument format: %s")
                return

        pid, ack, ts = self.drone_comms.send_loc_est(data)
        logger.info(
            "Sent LocEst (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_start_request(self, arg: str) -> None:  # noqa: ARG002
        """Send start request packet.

        Args:
            arg: Command argument (unused)
        """
        pid, ack, ts = self.drone_comms.send_start_request(StartRequestData())
        logger.info(
            "Sent StartRequest (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_start_response(self, arg: str) -> None:
        """Send start response packet.

        Args:
            arg: Command argument
        """
        parts = arg.split()
        success = True
        if parts and parts[0].lower() in ("false", "0", "no"):
            success = False

        data = StartResponseData(success=success)
        pid, ack, ts = self.drone_comms.send_start_response(data)
        logger.info(
            "Sent StartResponse (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_stop_request(self, arg: str) -> None:  # noqa: ARG002
        """Send stop request packet.

        Args:
            arg: Command argument (unused)
        """
        pid, ack, ts = self.drone_comms.send_stop_request(StopRequestData())
        logger.info(
            "Sent StopRequest (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_stop_response(self, arg: str) -> None:
        """Send stop response packet.

        Args:
            arg: Command argument
        """
        parts = arg.split()
        success = True
        if parts and parts[0].lower() in ("false", "0", "no"):
            success = False

        data = StopResponseData(success=success)
        pid, ack, ts = self.drone_comms.send_stop_response(data)
        logger.info(
            "Sent StopResponse (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_send_error(self, arg: str) -> None:  # noqa: ARG002
        """Send error packet.

        Args:
            arg: Command argument (unused)
        """
        pid, ack, ts = self.drone_comms.send_error(ErrorData())
        logger.info(
            "Sent Error (packet_id=%s, need_ack=%s, timestamp=%s)",
            pid,
            ack,
            ts,
        )

    def do_quit(self, arg: str) -> bool:  # noqa: ARG002
        """Quit the CLI.

        Args:
            arg: Command argument (unused)

        Returns:
            bool: True to exit
        """
        if self.started:
            self.do_stop("")
        return True

    def make_print_callback(self, pkt_type: str) -> Callable:
        """Create a callback function that prints packet data.

        Args:
            pkt_type: Type of packet this callback is for

        Returns:
            Callable: The callback function
        """

        def callback(data: object) -> None:
            logger.info("Received %s: %s", pkt_type, data)

        return callback


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser(description="GCS/FDS CLI")
    parser.add_argument(
        "--interface",
        choices=["serial", "simulated"],
        default="simulated",
        help="Radio interface type",
    )
    parser.add_argument("--port", help="Serial port (for serial interface)")
    parser.add_argument(
        "--baudrate",
        type=int,
        help="Serial baudrate (for serial interface)",
    )
    parser.add_argument("--host", help="TCP host (for simulated interface)")
    parser.add_argument(
        "--tcp-port",
        type=int,
        help="TCP port (for simulated interface)",
    )
    parser.add_argument(
        "--server-mode",
        action="store_true",
        help="Run in server mode (for simulated interface)",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Build radio config from args
    config_kwargs = {"interface_type": args.interface}
    if args.interface == "serial":
        if not args.port:
            logger.error("Serial port is required for serial interface")
            sys.exit(1)
        config_kwargs["port"] = args.port
        if args.baudrate:
            config_kwargs["baudrate"] = args.baudrate
    else:  # simulated
        if args.host:
            config_kwargs["host"] = args.host
        if args.tcp_port:
            config_kwargs["tcp_port"] = args.tcp_port
        if args.server_mode:
            config_kwargs["server_mode"] = True

    radio_config = RadioConfig(**config_kwargs)
    cli = GCSFDSCLI(radio_config)

    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        if cli.started:
            cli.do_stop("")


if __name__ == "__main__":
    main()
