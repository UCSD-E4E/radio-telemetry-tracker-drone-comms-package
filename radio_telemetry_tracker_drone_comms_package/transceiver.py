"""Module for handling radio packet transmission and reception with acknowledgment support."""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING, Callable

from radio_telemetry_tracker_drone_comms_package.proto import BasePacket, RadioPacket

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from radio_telemetry_tracker_drone_comms_package.interfaces import RadioInterface

MAX_PACKET_ID = 0x7FFFFFFF  # Maximum 31-bit signed integer

def _current_timestamp_us() -> int:
    """Return the current time in microseconds since epoch as an integer."""
    return int(time.time() * 1_000_000)

class PacketManager:
    """Manages radio packet transmission and reception with acknowledgment support."""

    def __init__(
        self,
        radio_interface: RadioInterface,
        ack_timeout: float = 2.0,
        max_retries: int = 5,
        on_ack_timeout: Callable[[RadioPacket], None] | None = None,
    ) -> None:
        """Initialize the PacketManager.

        Args:
            radio_interface: Interface for radio communication.
            ack_timeout: Time in seconds to wait for acknowledgment.
            max_retries: Maximum number of retransmission attempts.
            on_ack_timeout: Optional callback when packet acknowledgment times out.
        """
        self.radio_interface = radio_interface
        self.ack_timeout = ack_timeout
        self.max_retries = max_retries
        self.on_ack_timeout = on_ack_timeout

        self.send_queue: queue.PriorityQueue[tuple[int, float, RadioPacket]] = queue.PriorityQueue()
        # Maps packet_id -> { "packet": RadioPacket, "send_time": float, "retries": int }
        self.outstanding_acks = {}

        self._next_packet_id = 1
        self._id_lock = threading.Lock()

        # Thread control
        self._stop_event = threading.Event()
        self._send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)

    def start(self) -> None:
        """Start send/receive threads and connect the radio interface."""
        self.radio_interface.connect()
        self._stop_event.clear()
        self._send_thread.start()
        self._recv_thread.start()

    def stop(self) -> None:
        """Stop send/receive threads and close the radio interface."""
        self._stop_event.set()
        self._send_thread.join(timeout=2)
        self._recv_thread.join(timeout=2)
        self.radio_interface.close()

    def generate_packet_id(self) -> int:
        """Generate a unique packet ID between 1 and MAX_PACKET_ID."""
        with self._id_lock:
            if self._next_packet_id > MAX_PACKET_ID:
                self._next_packet_id = 1
            pid = self._next_packet_id
            self._next_packet_id += 1
        return pid

    def enqueue_packet(self, packet: RadioPacket) -> None:
        """Enqueue a packet for transmission.

        Priority is 0 if need_ack is True, else 1.
        """
        base = self._get_base(packet)
        priority = 0 if base.need_ack else 1
        self.send_queue.put((priority, time.time(), packet))

    def _send_loop(self) -> None:
        """Fetch packets from the queue to send, handle ack tracking."""
        while not self._stop_event.is_set():
            try:
                priority, enq_time, packet = self.send_queue.get(timeout=0.1)
            except queue.Empty:
                self._retry_outstanding_packets()
                continue

            self.radio_interface.send_packet(packet)
            base = self._get_base(packet)
            if base.need_ack:
                pid = base.packet_id
                self.outstanding_acks[pid] = {
                    "packet": packet,
                    "send_time": time.time(),
                    "retries": 0,
                }

    def _retry_outstanding_packets(self) -> None:
        """Check and retry outstanding packets if ack has not arrived in time."""
        now = time.time()
        to_remove = []
        for pid, info in self.outstanding_acks.items():
            if (now - info["send_time"]) >= self.ack_timeout:
                if info["retries"] < self.max_retries:
                    info["retries"] += 1
                    info["send_time"] = now
                    self.radio_interface.send_packet(info["packet"])
                else:
                    to_remove.append(pid)

        for pid in to_remove:
            timed_out_pkt = self.outstanding_acks[pid]["packet"]
            del self.outstanding_acks[pid]
            if self.on_ack_timeout:
                self.on_ack_timeout(timed_out_pkt)

    def _recv_loop(self) -> None:
        """Continuously attempt to receive packets and handle them."""
        while not self._stop_event.is_set():
            packet = self.radio_interface.receive_packet()
            if packet is None:
                continue
            self._handle_incoming_packet(packet)

    def _handle_incoming_packet(self, packet: RadioPacket) -> None:
        """Process incoming packets, removing from outstanding acks if relevant."""
        if packet.HasField("ack_pkt"):
            ack_id = packet.ack_pkt.ack_id
            if ack_id in self.outstanding_acks:
                del self.outstanding_acks[ack_id]
            return

        base = self._get_base(packet)
        if base.need_ack:
            self._send_ack(base.packet_id)

        # Let subclasses handle domain-specific logic
        self.on_user_packet_received(packet)

    def on_user_packet_received(self, packet: RadioPacket) -> None:
        """Hook for subclasses to handle a non-ACK packet."""

    def _send_ack(self, packet_id_to_ack: int) -> None:
        """Send an AckPacket for the given packet ID."""
        ack_pkt = RadioPacket()
        ack_pkt.ack_pkt.base.packet_id = self.generate_packet_id()
        ack_pkt.ack_pkt.base.need_ack = False
        ack_pkt.ack_pkt.base.timestamp = _current_timestamp_us()
        ack_pkt.ack_pkt.ack_id = packet_id_to_ack
        self.enqueue_packet(ack_pkt)

    @staticmethod
    def _get_base(packet: RadioPacket) -> BasePacket:
        """Return the BasePacket field for the RadioPacket."""
        field = packet.WhichOneof("msg")
        packet_types = {
            "ack_pkt": lambda p: p.ack_pkt.base,
            "syn_rqt": lambda p: p.syn_rqt.base,
            "syn_rsp": lambda p: p.syn_rsp.base,
            "cfg_rqt": lambda p: p.cfg_rqt.base,
            "cfg_rsp": lambda p: p.cfg_rsp.base,
            "gps_pkt": lambda p: p.gps_pkt.base,
            "ping_pkt": lambda p: p.ping_pkt.base,
            "loc_pkt": lambda p: p.loc_pkt.base,
            "str_rqt": lambda p: p.str_rqt.base,
            "str_rsp": lambda p: p.str_rsp.base,
            "stp_rqt": lambda p: p.stp_rqt.base,
            "stp_rsp": lambda p: p.stp_rsp.base,
            "err_pkt": lambda p: p.err_pkt.base,
        }
        if field in packet_types:
            return packet_types[field](packet)
        msg = "Unknown packet type in RadioPacket."
        raise ValueError(msg)
