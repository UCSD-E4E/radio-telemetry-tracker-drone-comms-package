import struct
import threading
import time
from typing import List, Optional, Callable, Dict
from rttsik.sik_radio import sikRadio
from rttsik.gcs_comms import GcsCommications
from rttsik.fds_comms import FdsComms


rad1 = sikRadio('/dev/ttyUSB0', '0', 57600)
rad2 = sikRadio('/dev/ttyUSB1', '1', 57600)
rad1.open()
rad2.open()


time.sleep(1)

gcs = GcsCommications(rad1)
fds = FdsComms(rad2)
gcs.add_radio('1')

gcs.start()
fds.start()

# gcs.set_ping_config(0, [1000])
