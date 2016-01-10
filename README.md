# bsbgateway
Read and write data on a [BSB](doc/protocol.md) (Boiler System Bus).

Functionalities offered:

 * [Commandline interface](doc/cmdline.md). Enter `help` to get list of commands, `help <cmd>` for documentation of a specific command.
 * [Web interface](doc/web.md) at port :8081 (e.g. http://localhost:8081)
 * [Logging of fields](doc/logging.md) with preset interval. The logs are written in ASCII `.trace` files and can be loaded with `trace/load_trace.py` into `numpy` arrays.

## Hardware

You need hardware to interface with the bus. In priniple, a serial port and a level converter / galvanic decoupler is required.
Schematic to be done. Have a look at http://www.mikrocontroller.net/topic/218643.

The serial port driver evaluates the `CTS` (clear-to-send) pin of the RS232 in order to check if the bus is free. Depending on your circuit, you may want to change the settings (esp. invert/no invert) in ([bsb_comm.py](bsbgateway/bsb/bsb_comm.py)), around line 60.

## Installation

Dependencies are web.py and pySerial.
On a debian-based system: `sudo apt-get install python-serial python-webpy`

Clone or download the project.

Edit `config.py` to your liking.

Run using `sh bsbgateway.sh`.

For continuous operation, it is (currently) recommendable to run in a `screen` environment like so:

`screen -dmS bsbgateway '/bin/sh /path/to/bsbgateway.sh'`
