import threading
import enum
from typing import List, Optional, Callable, Dict
from rttsik.sik_radio import sikRadio
from rttsik.packets import *

class Events(enum.Enum):
    PING_DETECTION_RECIEVED = 0x0
    HEARTBEAT_RECIEVED = 0x1
    TRANSMITTER_LOC_EST_RECIEVED = 0x2
    CONFIG_ACK_RECIEVED = 0x3
    COMMAND_ACK_RECIEVED = 0x4
    SEND_PING_FINDER = 0x5
    SEND_START = 0x6
    SEND_RESET = 0x7
    SEND_END = 0x8

class GcsCommications:
    def __init__(self, sik_radio: sikRadio):
        """
        Initialize the GCS communication interface.

        :param sik_radio: The sik radio interface.
        """
        self.sik_radio = sik_radio
        self.packet_ctr = 0
        self.fdscomms_list: List[str] = [] # List of known FdsComms addresses
        self.__receiver_thread: Optional(threading.Thread) = None
        self.__transmitter_thread: Optional(threading.Thread) = None
        self.__transmitter_queue = []
        self.__packet_map: Dict[int, List[Callable]] = {
            evt.value: [] for evt in Events
        }
        self.__running = False
        self.lock = threading.Lock()

    def add_radio(self, addr):
        self.fdscomms_list.append(addr)

    def start(self):
        """
        Start the GCS communication interface.
        """
        self.__running = True
        self.__receiver_thread = threading.Thread(target=self.__receiver_loop)
        self.__transmitter_thread = threading.Thread(target=self.__transmitter_loop)
        self.__receiver_thread.start()
        print("GCS communications started")

    def __receiver_loop(self):
        """
        Internal loop to recieve messages from FdsComms.
        """
        while self.__running:
            message = self.sik_radio.recieve()
            if message:
                if(len(message) >= 20): # can't do a checksum if the packet doesn't contain a checksum
                    self.__process_message(message)

    def __transmitter_loop(self):
        while self.__running:
            pass

    def __process_message(self, message: bytes):
        """
        Process incoming messages from FdsComms.

        :param message: The message recieved from a FdsComm.
        """
        type = Packet.get_type(message)

        # testing to make sure data recieved is correct
        
        print("Message:")
        print(message.hex())
        if(Packet.check_crc(message)):
            print("Printing data")
            hb_packet = Heartbeat_Packet.from_bytes(message)
            print(hb_packet.type)
            print(hb_packet.id)
            print(hb_packet.drone_latitude_degrees)
            print(hb_packet.drone_longitude_degrees)
            print(hb_packet.drone_altitude_meters)
            print(hb_packet.drone_heading_degrees)
            print(hb_packet.gps_state)
            print(hb_packet.ping_finder_state)
        # Decode header
        # Based off of header, accesses callables list from dictionary
        # Iterate through list
        else:
            print("failed")
        

    def set_ping_config(self, run_number_id: int, target_frequencies_hz: list[int], sampling_rate_hz: Optional[int] = None, gain_db: Optional[float] = None, 
            center_frequency_hz: Optional[int] = None, ping_width_ms: Optional[int] = None, ping_min_snr: Optional[int] = None, ping_max_length_multiplier: 
            Optional[float] = None, ping_min_length_multiplier: Optional[float] = None):
        # ACQUIRE LOCK FOR QUEUE
        self.lock.acquire()
        # create packet and place in transmitter queue
        config_packet = Set_Ping_Finder_Config_Packet(self.packet_ctr, run_number_id, target_frequencies_hz, sampling_rate_hz, gain_db, center_frequency_hz, 
                ping_width_ms, ping_min_snr, ping_max_length_multiplier, ping_min_length_multiplier)
        self.packet_ctr = self.packet_ctr + 1
        # send packet
        self.send_message(config_packet.to_packet())
        # RELEASE LOCK FOR QUEUE
        self.lock.release()

    def send_message(self, message: bytes, target_addr: Optional[str] = None):
        """
        Send a message to a specific FdsComm or broadcast to all.

        :param message: The message to send.
        :param target_addr: The address of the target FdsComm, or None to broadcast.
        """
        if target_addr:
            self.sik_radio.send(message, target_addr)
        else:
            # Broadcast to all known FdsComms
            for addr in self.fdscomm_list:
                self.sik_radio.send(message, addr)
        print(f"GCS sent messsage: {message.hex()} to {'all' if target_addr is None else target_addr}")
    

    def stop(self):
        """
        Stop the GCS communication interface.
        """
        self.__running = False
        if self.__receiver_thread:
            self.__receiver_thread.join()
        print("GCS communications stopped")

    def add_fdscomm(self, fdscomm_addr: str):
        """
        Add a MacComm to the list of known FdsComms.

        :param addr: The address of the FdsComm to add.
        """
        if fdscomm_addr not in self.fdscomms_list:
            self.fdscomms_list.append(fdscomm_addr)
            print(f"GCS added FdsComm: {fdscomm_addr}")

    def remove_fdscomm(self, fdscomm_addr: str):
        """
        Remove a FdsComm from the list of known FdsComm.

        :param fdscomm_addr: The address of the FdsComm to remove.
        """
        if fdscomm_addr in self.fdscomms_list:
            self.fdscomms_list.remove(fdscomm_addr)
            print(f"GCS removed FdsComm: {fdscomm_addr}")

