'''Configuration file template for BsbGateway.'''

################################################
# Python configuration

# See https://docs.python.org/2/library/logging.html on how to configure logging.
# You will probably want to set filename='something.log'.
import logging
logging.basicConfig(
    level='INFO',
    format='%(levelname)s %(name)s:%(lineno)d @%(relativeCreated)d -- %(message)s'
)

################################################
# Device configuration

# Type of connected device. Currently there is only a (incomplete) driver for Broetje ISR Plus.
# Read "driver" = "index of available fields".
device = 'broetje_isr_plus'

comm_interface = {
    # Type of connection. 'serial' for a serial adapter, 'network' for TCP connection
    # only the respective configuration ('adapter_settings'/'network_settings') will be used
    'type': 'network',

    # Settings for the used adapter.
    'adapter_settings' : {
        # * '/dev/ttyS0' ... '/dev/ttyS3' are usual devices for real serial ports.
        # * '/dev/ttyUSB0' is the usual device for a USB-to-serial converter on Linux.
        # * ':sim' opens a simple device simulation (no actual serial port required)
        #'adapter_device': ':sim',
        'adapter_device': 'COM5',

        # hardware settings - ignored when using simulation.
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
    },
    # Settings for the network connection
    'network_settings' : {
        'host': '192.168.0.59',
        'port': '6638',
        # flip all bits after receive + before send. If you use a simple BSB-to-UART
        # level converter, you most probably need to set this to True.
        'invert_bytes': True,
    }
};



# Bus adress offset of Gateway. Allowed range: 11 ... 125.
# (0 is the main device, 10 is the control panel).
# Gateway will use:
# This address for logging
# This address + 1 for cmdline requests
# This address + 2 for webinterface requests
bus_address = 23

# Minimum wait time between subsequent data requests on the bus. Used to avoid
# blocking up the bus when lots of requests come in at once.
# Note that the web interface has builtin timeout of 3.0 s. I.e. if you send
# more than (3.0 / min_wait_s) requests at once, the last ones will timeout.
min_wait_s = 0.1


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

# Fields to display as "dashboard" on the index page.
# List of lists, making up a table.
# You can set entries to None to leave gaps.
web_dashboard = [
    [ 700, 710, 8005, 8310, 8314],
    [ 1620, 1610, 8830, None, 8700],
]


################################################
# Leave this alone

import bsbgateway
bsbgateway.run(globals())
