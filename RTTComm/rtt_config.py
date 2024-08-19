class RTTConfig:
    def __init__(self, frequency=433e6, bandwidth=125e3, spreading_factor=10, coding_rate=8, preamble_length=12, sync_word=0x34, power=20):
        # Frequency: Center frequency for LoRa transmission (in Hz)
        self.frequency = frequency
        
        # Bandwidth: Signal bandwidth in Hz. Higher bandwidth allows for faster data rates but reduces sensitivity
        self.bandwidth = bandwidth
        
        # Spreading Factor: Number of chirps per symbol. Higher SF increases range but reduces data rate
        self.spreading_factor = spreading_factor
        
        # Coding Rate: Forward error correction rate. Higher rates offer better protection against interference but reduce data rate
        self.coding_rate = coding_rate
        
        # Preamble Length: Number of symbols sent at the start of a packet. Longer preambles improve reception reliability
        self.preamble_length = preamble_length
        
        # Sync Word: Identifier for network separation (devices must have the same sync word to communicate)
        self.sync_word = sync_word
        
        # Transmit Power: Output power for the LoRa radio (in dBm). Higher power increases range but consumes more energy
        self.power = power

    def load_from_file(self, config_file):
        # Load settings from a config file
        pass

    def save_to_file(self, config_file):
        # Save current settings to a config file
        pass