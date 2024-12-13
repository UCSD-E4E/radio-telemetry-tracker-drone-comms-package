import binascii
import struct
from typing import Optional
from datetime import datetime

# placeholder packet class
# packet contains a type, id, payload size and timestamp in the header, plus a 4 byte checksum at the end
class Packet:
    def __init__(self, id: int, packet_sent_timestamp: datetime):
        self.type = 0x0
        self.id = id
        self.data_length = 0
        self.packet_sent_timestamp = packet_sent_timestamp

    def to_packet(self):
        header = self.get_header()
        msg = header
        crc = binascii.crc32(msg)
        return msg + crc
    
    #def get_id(self):
    #    return self.id

    #def get_type(self):
    #    return self.type

    def get_header(self):
        header = struct.pack('<BBBIBBBBBI', self.type, self.id, self.data_length, self.packet_sent_timestamp.year, self.packet_sent_timestamp.month,
                self.packet_sent_timestamp.day, self.packet_sent_timestamp.hour, self.packet_sent_timestamp.minute, self.packet_sent_timestamp.second, 
                self.packet_sent_timestamp.microsecond)
        return header

    @classmethod
    def get_type(cls, packet: bytes):
        type_packed = packet[0:1]
        type = struct.unpack('<B', type_packed)
        return type
    
    @classmethod
    def get_id(cls, packet: bytes):
        id_packed = packet[1:2]
        id = struct.unpack('<B', id_packed)
        return id
    
    @classmethod
    def get_run_number_id(cls, packet: bytes):
        id_packed = packet[2:3]
        id = struct.unpack('<B', id_packed)
        return id
    
    @classmethod
    def get_time(cls, packet: bytes):
        date = packet[3:16]
        year, month, day, hour, minutes, seconds, microseconds = struct.unpack('<IBBBBBI', date)
        return datetime(year, month, day, hour, minutes, seconds, microseconds)
    
    @classmethod
    def get_payload(cls, packet: bytes):
        data_length_packed = packet[2:3]
        data_length = struct.unpack('<B', data_length_packed)[0]
        payload = packet[16:16+data_length]
        return payload
    
    @classmethod
    def generate_crc(cls, header: bytes, payload: bytes):
        msg = header + payload
        crc = binascii.crc32(msg)
        return crc
    
    @classmethod
    def check_crc(cls, packet: bytes):
        payload = Packet.get_payload(packet)
        header = packet[0:16]
        payload_size = struct.unpack('<B', packet[2:3])[0]
        recieved_crc = packet[16+payload_size:16+payload_size+4]
        crc = struct.pack('<I', Packet.generate_crc(header, payload))
        if(recieved_crc == crc):
            return 1
        else:
            return 0  

    
class Ping_Detection_Packet(Packet):
    def __init__(self, id: int, drone_latitude_degrees: float, drone_longitude_degrees: float, drone_altitude_meters: float, 
                transmitter_power_db: float, transmitter_frequency_hz: int, packet_sent_timestamp: datetime):
        self.type = 0x1
        self.id = id
        self.drone_latitude_degrees = drone_latitude_degrees
        self.drone_longitude_degrees = drone_longitude_degrees
        self.drone_altitude_meters = drone_altitude_meters
        self.transmitter_power_db = transmitter_power_db
        self.transmitter_frequency_hz = transmitter_frequency_hz
        self.packet_sent_timestamp = packet_sent_timestamp
        self.data_length = 20 

    def to_packet(self):
        header = super().get_header()
        payload = header + struct.pack('<ffffI', self.drone_latitude_degrees, self.drone_longitude_degrees, self.drone_altitude_meters, self.transmitter_power_db,
                self.transmitter_frequency_hz)
        crc = binascii.crc32(header + payload)
        return header + payload + crc
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Ping_Detection_Packet(id, 0, 0.0, 0.0, 0.0, 0, datetime.now())
        rebuilt_packet.drone_latitude_degrees, rebuilt_packet.drone_longitude_degrees, rebuilt_packet.drone_altitude_meters, rebuilt_packet.transmitter_power_db, rebuilt_packet.transmitter_frequency_hz = struct.unpack('<ffffI', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet

class Heartbeat_Packet(Packet):
    def __init__(self, id: int, drone_latitude_degrees: Optional[float] = None, drone_longitude_degrees: Optional[float] = None, drone_altitude_meters: Optional[float] = None,
                drone_heading_degrees: Optional[float] = None, gps_state: Optional[int] = None, ping_finder_state: Optional[int] = None):
        self.type = 0x2
        self.id = id
        self.drone_latitude_degrees = drone_latitude_degrees
        if(drone_latitude_degrees is None):
            self.drone_latitude_degrees_valid = 0
            self.drone_latitude_degrees = 0
        else:
            self.drone_latitude_degrees_valid = 1
            self.drone_latitude_degrees = drone_latitude_degrees
        if(drone_longitude_degrees is None):
            self.drone_longitude_degrees_valid = 0
            self.drone_longitude_degrees = 0
        else:
            self.drone_longitude_degrees_valid = 1
            self.drone_longitude_degrees = drone_longitude_degrees
        if(drone_altitude_meters is None):
            self.drone_altitude_meters_valid = 0
            self.drone_altitude_meters = 0
        else:
            self.drone_altitude_meters_valid = 1
            self.drone_altitude_meters = drone_altitude_meters
            
        if(drone_heading_degrees is None):
            self.drone_heading_degrees = 0
        else: 
            self.drone_heading_degrees = drone_heading_degrees
        self.gps_state = gps_state
        self.ping_finder_state = ping_finder_state
        self.packet_sent_timestamp = datetime.now()
        self.data_length = 15 + 12
    
    def to_packet(self):
        header = super().get_header()
        payload = struct.pack('<f?f?f?fII', self.drone_latitude_degrees, self.drone_latitude_degrees_valid, self.drone_longitude_degrees, self.drone_longitude_degrees_valid, 
                self.drone_altitude_meters, self.drone_altitude_meters_valid, self.drone_heading_degrees, self.gps_state, self.ping_finder_state)
        crc = binascii.crc32(header + payload)
        return header + payload + struct.pack('<I', crc)
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Heartbeat_Packet(id)
        rebuilt_packet.drone_latitude_degrees, rebuilt_packet.drone_latitude_degrees_valid, rebuilt_packet.drone_longitude_degrees, rebuilt_packet.drone_longitude_degrees_valid, rebuilt_packet.drone_altitude_meters, rebuilt_packet.drone_altitude_meters_valid, rebuilt_packet.drone_heading_degrees, rebuilt_packet.gps_state, rebuilt_packet.ping_finder_state = struct.unpack('<f?f?f?fII', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet
    
class Trx_Loc_Estimation_Packet(Packet):
    def __init__(self, id: int, transmitter_frequency_hz: int, transmitter_latitude_degrees: float, transmitter_longitude_degrees: float, 
                transmitter_altitude_meters: float, packet_sent_timestamp: datetime):
        self.type = 0x3
        self.id = id
        self.transmitter_frequency_hz = transmitter_frequency_hz
        self.transmitter_latitude_degrees = transmitter_latitude_degrees
        self.transmitter_longitude_degrees = transmitter_longitude_degrees
        self.transmitter_altitude_meters = transmitter_altitude_meters
        self.packet_sent_timestamp = packet_sent_timestamp
        self.data_length = 21

    def to_packet(self):
        header = super().get_header()
        payload = struct.pack('<Ifff', self.transmitter_frequency_hz, self.transmitter_latitude_degrees, self.transmitter_longitude_degrees,
                self.transmitter_altitude_meters)
        crc = binascii.crc32(header + payload)
        return header + payload + struct.pack('<I', crc)
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Trx_Loc_Estimation_Packet(id, 0, 0.0, 0.0, 0.0, datetime.now())
        rebuilt_packet.transmitter_frequency_hz, rebuilt_packet.transmitter_latitude_degrees, rebuilt_packet.transmitter_longitude_degrees, rebuilt_packet.transmitter_altitude_meters = struct.unpack('<Ifff', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet
    
    
class Config_Ack_Packet(Packet):
    def __init__(self, id: int, success: bool, message, packet_sent_timestamp: datetime):
        self.type = 0x4
        self.id = id
        self.success = success
        self.message = message
        self.packet_sent_timestamp = packet_sent_timestamp
        self.data_length = len(message) + 6

    def to_packet(self):
        header = super().get_header()
        payload = struct.pack('<?s', self.success, self.message)
        crc = binascii.crc32(header + payload)
        return header + payload + crc
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Config_Ack_Packet(id, 0, 0, datetime.now())
        rebuilt_packet.success, rebuilt_packet.message = struct.unpack('<?s', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet
    
class Command_Ack_Packet(Packet):
    def __init__(self, id: int, success: bool, message, packet_sent_timestamp: datetime):
        self.type = 0x5
        self.id = id
        self.success = success
        self.message = message
        self.packet_sent_timestamp = packet_sent_timestamp
        self.data_length = len(message) + 6

    def to_packet(self):
        header = super().get_header()
        payload = header + struct.pack('<?s', self.success, self.message)
        crc = binascii.crc32(header + payload)
        return header + payload + crc
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Command_Ack_Packet(id, 0, 0, datetime.now())
        rebuilt_packet.success, rebuilt_packet.message = struct.unpack('<?s', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet
        
class Set_Ping_Finder_Config_Packet(Packet):
    def __init__(self, id: int, run_number_id: int, target_frequencies_hz: list[int], sampling_rate_hz: Optional[int] = None, gain_db: Optional[float] = None, 
            center_frequency_hz: Optional[int] = None, ping_width_ms: Optional[int] = None, ping_min_snr: Optional[int] = None, ping_max_length_multiplier:
            Optional[float] = None, ping_min_length_multiplier: Optional[float] = None):
        self.type = 0x6
        self.id = id
        self.run_number_id = run_number_id
        self.target_frequencies_hz = target_frequencies_hz
        self.target_frequencies_hz_length = len(target_frequencies_hz)
        if(sampling_rate_hz is None):
            self.sampling_rate_hz = 2500000
        else:
            self.sampling_rate_hz = sampling_rate_hz
        if(gain_db is None):
            self.gain_db = 56.0
        else:
            self.gain_db = gain_db
        if(center_frequency_hz is None):
            sum = 0
            for n in self.target_frequencies_hz:
                sum = sum + n
            self.center_frequency_hz = int(sum / len(self.target_frequencies_hz))
        else:
            self.center_frequency_hz = center_frequency_hz
        if(ping_width_ms is None):
            self.ping_width_ms = 25
        else:
            self.ping_width_ms = ping_width_ms
        if(ping_min_snr is None):
            self.ping_min_snr = 25
        else:
            self.ping_min_snr = ping_min_snr
        if(ping_max_length_multiplier is None):
            self.ping_max_length_multiplier = 1.5
        else:
            self.ping_max_length_multiplier = ping_max_length_multiplier
        if(ping_min_length_multiplier is None):
            self.ping_min_length_multiplier = 0.5
        else:
            self.ping_min_length_multiplier = ping_min_length_multiplier
        self.packet_sent_timestamp = datetime.now()
        self.data_length = (self.target_frequencies_hz_length + 1) * 4 + 8*4

    def to_packet(self):
        header = super().get_header()
        frequency_list = struct.pack('<I', self.target_frequencies_hz_length)
        for i in self.target_frequencies_hz:
            frequency_list += struct.pack('<I', i)
        payload = struct.pack('<I', self.run_number_id) + frequency_list + struct.pack('IfIIIff', self.sampling_rate_hz, self.gain_db, 
                self.center_frequency_hz, self.ping_width_ms, self.ping_min_snr, self.ping_max_length_multiplier, self.ping_min_length_multiplier)
        return header + payload + struct.pack('<I', super().generate_crc(header, payload))
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Set_Ping_Finder_Config_Packet(id, 0, [1])
        rebuilt_packet.run_number_id = super().get_run_number_id(packet)
        rebuilt_packet.target_frequencies_hz_length = struct.unpack('<I', payload[0:4])[0]
        target_freq_list = []
        for i in range(rebuilt_packet.target_frequencies_hz_length):
            target_freq_list.append(struct.unpack('<I', payload[(i+1)*4:(i+2)*4])[0])
        rebuilt_packet.target_frequencies_hz = target_freq_list
        offset = (rebuilt_packet.target_frequencies_hz_length + 1) * 4
        payload = payload[offset:offset+28]
        rebuilt_packet.sampling_rate_hz, rebuilt_packet.gain_db, rebuilt_packet.center_frequency_hz, rebuilt_packet.ping_width_ms, rebuilt_packet.ping_min_snr, rebuilt_packet.ping_max_length_multiplier, rebuilt_packet.ping_min_length_multiplier = struct.unpack('<IfIIIff', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet

    
class Config_Ack_Packet(Packet):
    def __init__(self, id: int, success: bool, packet_sent_timestamp: datetime):
        self.type = 0x7
        self.id = id
        self.success = success
        self.packet_sent_timestamp = packet_sent_timestamp
        self.data_length = 1

    def to_packet(self):
        header = super().get_header()
        msg = header + struct.pack('<?', self.success)
        crc = binascii.crc32(msg)
        return msg + crc
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Config_Ack_Packet(id, 0, 0, datetime.now())
        rebuilt_packet.success = struct.unpack('<?', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet

class Command_Ack_Packet(Packet):
    def __init__(self, id: int, success: bool, command_type: int, packet_sent_timestamp: datetime):
        self.type = 0x8
        self.id = id
        self.success = success
        self.command_type = command_type
        self.packet_sent_timestamp = packet_sent_timestamp
        self.data_length = 5

    def to_packet(self):
        header = super().get_header()
        msg = header + struct.pack('<?I', self.success, self.command_type)
        crc = binascii.crc32(msg)
        return msg + crc
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Command_Ack_Packet(id, 0, 0, datetime.now())
        rebuilt_packet.success, rebuilt_packet.command_type = struct.unpack('<?I', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet
    
class Command_Packet(Packet):
    def __init__(self, id: int, command_type: int):
        self.type = 0x9
        self.id = id
        self.command_type = command_type
        self.packet_sent_timestamp = datetime.now()
        self.data_length = 4
    
    def to_packet(self):
        header = super().get_header()
        msg = header + struct.pack('<I', self.command_type)
        crc = binascii.crc32(msg)
        return msg + crc
    
    @classmethod
    def from_bytes(cls, packet: bytes) -> Packet:
        id = super().get_id(packet)[0]
        payload = super().get_payload(packet)
        rebuilt_packet = Command_Ack_Packet(id, 0, 0, datetime.now())
        rebuilt_packet.command_type = struct.unpack('<I', payload)
        rebuilt_packet.packet_sent_timestamp = super().get_time(packet)
        return rebuilt_packet