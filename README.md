# Radio Telemetry Tracker Drone Communications Package (Comms Package)

The **Radio Telemetry Tracker Drone Communications Package** is a Python-based library designed to facilitate the transmission, reception, and handling of protobuf-based radio packets between a drone's field device software ([FDS](https://github.com/UCSD-E4E/radio-telemetry-tracker-drone-fds)) and the ground control station ([GCS](https://github.com/UCSD-E4E/radio-telemetry-tracker-drone-gcs)). It implements reliable communication through packet acknowledgements, serialization/deserialization of Protobuf messages, and provides an extendable structure for new message types.

> Note: This package is not intended for end-user use in standalone mode. Rather, it is a shared component that is consumed by the FDS and GCS repositories. Therefore, detailed user-facing instructions are provided in the respective repositories where this package is integrated.

## Table of Contents
- [Radio Telemetry Tracker Drone Communications Package (Comms Package)](#radio-telemetry-tracker-drone-communications-package-comms-package)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Usage](#usage)
  - [Troubleshooting](#troubleshooting)
  - [License](#license)

## Overview

This package provides:

- **Packet Definitions**: Protobuf message definitions for radio telemetry data and requests
- **Codec**: Encoding/decoding logic with framing, CRC checks, and synchronization markers
- **Radio Interfaces**:
  - **SerialRadioInterface**: For physical serial (UART) connections
  - **SimulatedRadioInterface**: For TCP-based simulation and testing
- **Packet Management**: Reliable transmission with retry and acknowledgment (ACK) mechanisms
- **DroneComms Class**: High-level API with typed handlers and callback registration

## Prerequisites

- Python 3.12 or later
- Poetry 1.8 or later
- For serial communication: `pyserial`
- For protocol buffers: `protobuf`, `grpcio-tools`

## Installation

1. Add as a dependency to your project:

    ```bash
    poetry add git+https://github.com/UCSD-E4E/radio-telemetry-tracker-drone-comms-package.git
    ```

2. Or clone for development:
    ```bash
    git clone https://github.com/UCSD-E4E/radio-telemetry-tracker-drone-comms-package.git
    cd radio-telemetry-tracker-drone-comms-package
    poetry install
    ```

## Configuration

The library supports two interface types:

1. **Serial Interface**:

  ```python
  from radio_telemetry_tracker_drone_comms_package import RadioConfig

  config = RadioConfig(
    interface_type="serial",
    port="/dev/ttyUSB0", # Serial port
    baudrate=56700, # Communication speed
  )
```

2. **Simulated Interface** (for testing):

  ```python
  config = RadioConfig(
    interface_type="simulated",
    host="localhost", # TCP host
    tcp_port=50000, # TCP port
    server_mode=False, # Client/server mode
  )
  ```

## Usage

Basic usage pattern:

```python
from radio_telemetry_tracker_drone_comms_package import DroneComms, RadioConfig, GPSData
```

1. **Initialize communications**:
    ```python
    config = RadioConfig(interface_type="serial", port="/dev/ttyUSB0")
    comms = DroneComms(radio_config=config)
    ```     

2. **Register handlers for incoming packets**:
    ```python
    def on_gps_data(data: GPSData):
      print(f"GPS: {data.easting}, {data.northing}, {data.altitude}")

    comms.register_gps_handler(on_gps_data)
    ```

3. **Start communication**:
    ```python
    comms.start()  # Opens the radio interface and starts Rx/Tx threads
    ```

4. **Send packets as needed**:
    ```python
    comms.send_sync_request(SyncRequestData())
    ```

5. **Clean up when done**:
    ```python
    comms.stop()  # Closes the radio interface and stops threads
    ```


## Troubleshooting

Common issues and solutions:

- **No Packets Received**
  - Check physical connections (serial) or network connectivity (TCP)
  - Verify correct port/baudrate settings
  - Look for exceptions in logs

- **CRC Errors**
  - Ensure matching Protobuf versions between FDS and GCS
  - Check for packet framing issues
  - Verify byte order consistency

- **Timeouts**
  - Increase `read_timeout` or `ack_timeout` for slow/unreliable links
  - Check for network congestion or interference
  - Verify both ends are running and properly configured

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.



