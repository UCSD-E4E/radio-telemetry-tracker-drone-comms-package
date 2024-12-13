import struct
import serial
import threading
from typing import Optional, Tuple

class sikRadio:
    def __init__(self, port: str, device_addr: str, baudrate: int = 57600):
        """
        Initialize the sik radio interface

        :param port: the serial port the sik radio is connected to.
        :param device_addr: the address of the device.
        :param baudrate: the baud rate of the serial port.
        """
        self.port = port
        self.device_addr = device_addr
        self.baudrate = baudrate
        self.serial = None
        self.__lock = threading.Lock()
    
    def open(self):
        """
        Opens the sik radio serial connectoin.
        """
        self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
        print(f"sik radio opened on {self.port} with baudrate {self.baudrate}")

    def close(self):
        """
        Closes the sik radio serial connection.
        """
        if self.serial and self.serial.is_open:
            self.serial.close()
        print("sik radio closed")

    def send(self, message: bytes, addr: Optional[str] = None):
        """
        Sends a message to the specified address.

        :param message: the message to send.
        :param addr: the address to send the message to. None for broadcast.
        """
        with self.__lock:
            if addr:
                packet = f"{addr:}:".encode('ascii') + message
            else:
                packet = message
            
            print("sending " + packet.hex())
            if self.serial and self.serial.is_open:
                self.serial.write(packet)
                # print(f"Sent message to {'broadcast' if addr is None else addr}: {message.hex()}")
            else:
                print(f"Serial connection not open")

    def recieve(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Recieve a message.

        :return: a tuple containing the recieved message, or None if the message is not intended for this device.
        """
        # data = self.serial.readline().strip()
        with self.__lock:
            if self.serial and self.serial.is_open:
                try:
                    data = self.serial.readline().strip()
                    if b':' in data:
                        target_addr, message = data.split(b':', 1)
                        target_addr = target_addr.decode('ascii')
                        if target_addr == self.device_addr:
                            print(f"Recieved message for {self.device_addr}: {message.hex()}")
                            return message
                        else:
                            print(f"Message not intended for this device (intended for {target_addr})")
                            return None
                    else:
                        # If no address is provided, assume broadcast and accept the message
                        # print(f"Recieved broadcast message: {data.hex()}")
                        return data
                except Exception as e:
                    print(f"Error recieving message: {e}")
                    return None
            else:
                print(f"Serial connection not open")
                return None