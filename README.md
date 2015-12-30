# bsbgateway
Read and write data on a [BSB](doc/protocol.md) (Boiler System Bus).

Functionalities offered:

 * [Commandline interface](doc/cmdline.md). Enter `help` to get list of commands, `help <cmd>` for documentation of a specific command.
 * [Web interface](doc/web.md) at port :8081 (e.g. http://localhost:8081)
 * [Logging of fields](doc/logging.md) with preset interval. The logs are written in ASCII `.trace` files. Format description and viewer are to be done...

## Installation

Dependencies are web.py and pySerial.
On a debian-based system: `sudo apt-get install python-serial python-webpy`

Clone or download the project.

Edit `config.py` to your liking.

Run using `sh bsbgateway.sh`.

For continuous operation, it is (currently) recommendable to run in a `screen` environment like so:

`screen -dmS bsbgateway '/bin/sh /path/to/bsbgateway.sh'`
