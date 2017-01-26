'''Configuration file template for BsbGateway.'''

################################################
# Python configuration

# See https://docs.python.org/2/library/logging.html on how to configure logging.
# You will probably want to set filename='something.log'.
import logging
logging.basicConfig(level='DEBUG', format='%(levelname)s %(name)s:%(lineno)d -- %(message)s')

################################################
# Device configuration

# Type of connected device. Currently there is only a (incomplete) driver for Broetje ISR Plus.
# Read "driver" = "index of available fields".
device = 'broetje_isr_plus'

# Settings for the used adapter.
adapter_settings = {
    # * 'fake' = use a fake serial device, see below.
    #     The fake device answers get and set telegrams with appropriate replies. Set values are remembered for the session.
    # * 'serial' = use a serial port (real or USB)
    'adapter_type': 'serial',
    
    # * '/dev/ttyS0' ... '/dev/ttyS3' are usual devices for real serial ports.
    # * '/dev/ttyUSB0' is the usual device for a USB-to-serial converter on Linux.
    'adapter_device': '/dev/ttyUSB0',
    
    # hardware settings - only applicable if adapter_type is 'serial'.
    # see also bsbgateway/serial_source.py
    # baud rate - 4800 for BSB bus
    'port_baud': 4800,
    # 1, 1.5 or 2 - 1 for BSB bus
    'port_stopbits': 1,
    # 'odd' or 'even'. For BSB: 'odd' if you invert bytes (see below), 'even' if not.
    'port_parity': 'odd',
    # flip all bits after receive + before send. If you use a simple BSB-to-UART
    # level converter, you most probably need to set this to True.
    'invert_bytes': True,
    # Only send if CTS has this state (True or False); None to disable.
    # Use this if your adapter has a "bus in use" detection wired to CTS pin of the RS232 interface.
    'expect_cts_state': None,
    # wait time in seconds if blocked by CTS (see above).
    'write_retry_time': 0.005,
}

# Bus adress offset of Gateway. Allowed range: 11 ... 125.
# (0 is the main device, 10 is the control panel).
# Gateway will use:
# This address for logging
# This address + 1 for cmdline requests
# This address + 2 for webinterface requests
bus_address = 23


################################################
# Logger configuration

# Global log timer interval. Determines the "time slice" for logging.
# Signals cannot be logged faster than that; and every logger's period
# has to be a multiple of this. Unit = seconds.
atomic_interval = 5

# Path to store the trace files in.
# (Filename = <tracefile_dir>/<disp_id>.trace )
tracefile_dir = 'traces'

# Fields to be logged and logging interval in seconds.
# List of tuples: (Disp_ID, Interval).
# The disp_id can be found on the device control panel
# or by using the LIST and INFO commands of the commandline interface.
# Interval in seconds MUST be a multiple of atomic_interval.
loggers = [
    (8510, 5), # Kollektortemperatur
    (8310, 300), # Kesseltemperatur
    (8830, 300), # TW-Temperatur 1
    (8832, 300), # TW-Temperatur unten
    (8743, 300), # Vorlauftemp. 1
    (8700, 300), # Aussentemperatur
    (8003, 300), # Status TW
    (8007, 5), # Status Solar
]

# Triggers for email notification.
# Tuple (Disp_ID, Trigger type, threshold(s)).
# Triggertypes currently defined are: 'rising_edge', 'falling_edge' (1 Threshold value)
#  Threshold = in units of the (decoded) field value.
# After each trigger event, six hours of dead time apply.
# Triggers only work if there is a LOGGER defined for the field.

triggers = [
# Example: notify when value of 8700 falls below 10.0.
#    (8700, 'falling_edge', 10.0),
]

# Email recipient
emailaddress = 'recipient@domain.com'
# SMTP server and credentials for sending email notifications
emailserver = 'smtp.domain.com'
emailcredentials = ('loginname', 'password')


################################################
# Cmdline interface configuration

cmd_interface_enable = True


################################################
# Web interface configuration

# Use the web interface?
web_interface_enable = True

# Port on which the web interface shall listen.
web_interface_port = 8081


################################################
# Leave this alone

import bsbgateway
bsbgateway.run(globals())