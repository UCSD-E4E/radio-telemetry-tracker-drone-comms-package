import struct

class RTTLoRaPacket:
    def __init__(self, frequencies=None, amplitudes=None, latitude=0.0, longitude=0.0, payload_id=0):
        self.frequencies = frequencies or []
        self.amplitudes = amplitudes or []
        self.latitude = latitude
        self.longitude = longitude
        self.payload_id = payload_id

    def to_bytes(self) -> bytes:
        data = struct.pack('<d', self.latitude) + struct.pack('<d', self.longitude)
        for freq, amp in zip(self.frequencies, self.amplitudes):
            data += struct.pack('<f', freq) + struct.pack('<f', amp)
        return data

    @classmethod
    def from_bytes(cls, data: bytes):
        latitude, longitude = struct.unpack('<dd', data[:16])
        frequencies = []
        amplitudes = []
        for i in range(16, len(data), 8):
            freq, amp = struct.unpack('<ff', data[i:i+8])
            frequencies.append(freq)
            amplitudes.append(amp)
        return cls(frequencies, amplitudes, latitude, longitude)
















