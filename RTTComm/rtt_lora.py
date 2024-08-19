import serial
import time
import threading
from .rtt_config import RTTConfig
from .rtt_exceptions import RTTCommError

class RTTComm:
    def __init__(self, config: RTTConfig, port="/dev/tty/USB0", baudrate=9600, timeout=1, send_receive_interval=0.05):
        self.config = config
        self.serial_port = serial.Serial(port, baudrate, timeout=timeout)
        self.send_receive_interval = send_receive_interval
        self.running = False

    def initialize(self):
        self.set_frequency(self.config.frequency)
        self.set_power(self.config.power)

    def set_frequency(self, frequency):
        # Command to set the frequency on the LoRa module
        pass

    def set_power(self, power_level):
        # Command to set the power level on the LoRa module
        pass

    def send_packet(self, packet: bytes):
        try:
            self.serial_port.write(packet)
        except serial.SerialException as e:
            raise RTTCommError(f"Failed to send packet: {str(e)}")

    def receive_packet(self) -> bytes:
        try:
            packet = self.serial_port.read(256)
            return packet
        except serial.SerialException as e:
            raise RTTCommError(f"Failed to receive packet: {str(e)}")

    def start_communication(self, send_function, receive_function):
        """Start the communicaiton loop for sending and receiving"""
        self.running = True
        threading.Thread(target=self._send_and_receive, args=(send_function, receive_function)).start()

    def stop_communication(self):
        """Stop the communication loop"""
        self.running = False

    def _communication_loop(self, send_function, receive_function):
        while self.running:
            # Send data
            send_function()
            # Wait for interval
            time.sleep(self.send_receive_interval)
            # Receive data
            received_packet = self.receive_packet()
            if received_packet:
                receive_function(received_packet)
            # Wait for the inverva before the next send/receive cycle
            time.sleep(self.send_receive_interval)
    
    def close(self):
        self.serial_port.close()


            























