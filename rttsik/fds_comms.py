import struct
import threading
import enum
import time
from rttsik.packets import *
from typing import List, Optional, Callable, Dict
from rttsik.sik_radio import sikRadio
from rttsik.drone_state import *

class Events(enum.Enum):
    SEND_PING_DETECTION = 0x0
    SEND_HEARTBEAT = 0x1
    SEND_TRANSMITTER_LOC_EST = 0x2
    SEND_CONFIG_ACK = 0x3
    SEND_COMMAND_ACK = 0x4
    PING_FINDER_RECIEVED = 0x5
    START_RECIEVED = 0x6
    RESET_RECIEVED = 0x7
    END_RECIEVED = 0x8

class FdsComms:
    def __init__(self, sik_radio: sikRadio):
        """
        Initialize the fds communication interface.

        :param sik_radio: The sik radio interface.
        """
        self.sik_radio = sik_radio
        self.__receiver_thread = threading.Thread(target=self.__receiver_loop)
        self.__receiver_thread.start()
        self.__transmitter_thread: Optional(threading.Thread) = None
        self.__heartbeat_thread: Optional(threading.Thread) = None
        self.__transmitter_queue = []
        self.transmitter_lock = threading.Lock()
        self.__packet_map: Dict[int, List[Callable]] = {
            evt.value: [] for evt in Events
        }
        self.__running = False

        self.packet_ctr = 0
        self.drone_latitude_degrees: Optional[float] = None
        self.drone_longiude_degrees: Optional[float] = None
        self.drone_altitude_meters: Optional[float] = None
        self.drone_heading_degrees: Optional[float] = None
        self.gps_state = GPSState.NOT_READY
        self.ping_finder_state = PingFinderState.NOT_READY

    def start(self):
        """
        Start the GCS communication interface.
        """
        self.__running = True
        
        self.__transmitter_thread = threading.Thread(target=self.__transmitter_loop)
        self.__heartbeat_thread = threading.Thread(target=self.__heartbeat_loop)
        self.__heartbeat_thread.start()
        self.__transmitter_thread.start()
        print("FdsComms communications started")

    def __receiver_loop(self):
        """
        Internal loop to recieve messages from FdsComms.
        """
        while True:
            message = self.sik_radio.recieve()
            if message:
                if(len(message) >= 20): # can't do a checksum if you don't have the checksum
                    self.__process_message(message)
            
            time.sleep(0.1)

    def __process_message(self, message: bytes):
        packet_type = Packet.get_type(message)
        if(Packet.check_crc(message)):
            if(packet_type[0] == 0x6):
                self.__process_config(message)
        else:
            print("fail")


    def __process_config(self, packet: bytes):
        config = Set_Ping_Finder_Config_Packet.from_bytes(packet)
        
        pass

    def __heartbeat_loop(self):
        while self.__running:
            self.transmitter_lock.acquire()
            # add a heartbeat to the transmitter queue
            hb_packet = Heartbeat_Packet(self.packet_ctr, self.drone_latitude_degrees, self.drone_longiude_degrees, self.drone_altitude_meters, self.drone_heading_degrees, 
                    self.gps_state, self.ping_finder_state)
            self.sik_radio.send(hb_packet.to_packet())     
            self.packet_ctr = self.packet_ctr + 1
            self.transmitter_lock.release()
            time.sleep(2)

    def __transmitter_loop(self):
        while self.__running:
            self.transmitter_lock.acquire()
            if len(self.__transmitter_queue) > 0:
                self.sik_radio.send(self.__transmitter_queue[0])
                self.__transmitter_queue[0].pop(0)
            self.transmitter_lock.release()