import threading
from typing import List, Optional
from lora_radio import LoRaRadio


class GcsCommications:
    def __init__(self, lora_radio: LoRaRadio):
        """
        Initialize the GCS communication interface.

        :param lora_radio: The LoRa radio interface.
        """
        self.lora_radio = lora_radio
        self.mavcomms_list = List[str] = []  # List of known MavComms addresses
        self.__receiver_thread: Optional(threading.Thread) = None
        self.__running = False

    def start(self):
        """
        Start the GCS communication interface.
        """
        self.__running = True
        self.__receiver_thread = threading.Thread(target=self.__receiver_loop)
        self.__reciever_thread.start()
        print("GCS communications started")

    def __receiver_loop(self):
        """
        Internal loop to recieve messages from MavComms.
        """
        while self.__running:
            message = self.lora_radio.recieve()
            if message:
                self.__process_message(message)

    def __process_message(self, message: bytes):
        """
        Process incoming messages from MavComms.

        :param message: The message recieved from a MavComm.
        """
        pass

    def send_message(self, message: bytes, target_addr: Optional[str] = None):
        """
        Send a message to a specific MavComm or broadcast to all.

        :param message: The message to send.
        :param target_addr: The address of the target MavComm, or None to broadcast.
        """
        if target_addr:
            self.lora_radio.send(message, target_addr)
        else:
            # Broadcast to all known MavComms
            for addr in self.mavcomms_list:
                self.lora_radio.send(message, addr)
        print(f"GCS sent messsage: {message.hex()} to {'all' if target_addr is None else target_addr}")
    
    def stop(self):
        """
        Stop the GCS communication interface.
        """
        self.__running = False
        if self.__receiver_thread:
            self.__receiver_thread.join()
        print("GCS communications stopped")

    def add_mavcomm(self, mavcomm_addr: str):
        """
        Add a MacComm to the list of known MavComms.

        :param addr: The address of the MavComm to add.
        """
        if mavcomm_addr not in self.mavcomms_list:
            self.mavcomms_list.append(mavcomm_addr)
            print(f"GCS added MavComm: {mavcomm_addr}")

    def remove_mavcomm(self, mavcomm_addr: str):
        """
        Remove a MavComm from the list of known MavComms.

        :param mavcomm_addr: The address of the MavComm to remove.
        """
        if mavcomm_addr in self.mavcomms_list:
            self.mavcomms_list.remove(mavcomm_addr)
            print(f"GCS removed MavComm: {mavcomm_addr}")










