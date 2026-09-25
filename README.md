# bsbgateway
Read and write data on a [BSB](doc/protocol.md) (Boiler System Bus).

Functionalities offered:

 * [Commandline interface](doc/cmdline.md). Enter `help` to get list of commands, `help <cmd>` for documentation of a specific command.
 * [Web interface](doc/web.md) at port :8082 (e.g. http://localhost:8082)
 * [MQTT Interface](doc/mqtt.md) for interfacing with Home Assistant (or other MQTT endpoints)
 * [Logging of fields](doc/logging.md) with preset interval. The logs are written in ASCII `.trace` files and can be loaded with `trace/load_trace.py` into `numpy` arrays.

 ## If you are updating from a previous version

 The project underwent significant modernizations at the beginning of 2026. Be sure to read the installation docs. The old config.py is obsolete and has to be replaced by the new `bsbgateway.ini`. There is now an interactive configuration menu to help with this.


## Hardware

You need hardware to interface with the bus. In principle, a serial port and a level converter / galvanic decoupler is required.
The circuit that I use is drawn [here](doc/hardware.md), but not recommended for rebuilding.

The serial port driver evaluates the `CTS` (clear-to-send) pin of the RS232 in order to check if the bus is free. Depending on your circuit, you may want to change the settings (esp. invert/no invert) in the configuration. 


## Installation

The easiest way is to install using `pipx`:

`pipx install bsbgateway`

Alternatively and/or for hacking, you can clone the repository, then run `bsbgateway.sh`. It will automatically setup a local venv, install the project in editable mode and run it.

In both cases, you get `bsbgateway` as user-mode-program. In order to set it up and configure as system service, use the management mode (`bsbgateway manage`). See following sections.

You will need a device description file. See [devices](https://github.com/loehnertj/bsbgateway/tree/master/devices)

## After installation

In the terminal, run `bsbgateway manage`. This will show a menu with the options:

* Configure: Interactive configuration;
* Run: run the gateway within the terminal (for testing). Same happens if you just start `bsbgateway` without parameters.
* Install / uninstall / restart service: to manage system service.

### Configuring

The default config file is `bsbgateway.ini`.

Upon start, it will be searched in (in this order):

* working dir
* `~/.config/bsbgateway/` (recommended location)
* `/etc/bsbgateway/`

You can give the `--config /path/to/something.ini` switch to use a specific `ini` file instead of the default.

After editing the file, it is saved back to the same location. If it doesn't yet exist, `~/.config/bsbgateway/bsbgateway.ini` is created.

In a fresh installation, configure at least the following:

* Gateway / Device - point to your device json file (see below)
* Adapter - if using a serial adapter, check at least the "Adapter Device" and "Invert bytes" settings.

Config is saved when you return to the main menu, unless you discard the changes with `x`.

#### Example: Minimal Configuration

Here's what a minimal `bsbgateway.ini` might look like for a Broetje ISR heater connected via USB-to-RS232 adapter:

```ini
[gateway]
; "broetje_isr_plus.json" expected in config directory!
device = broetje_isr_plus

[adapter]
adapter_type = serial
adapter_device = /dev/ttyUSB0
invert_bytes = True
port_parity = odd
expect_cts_state = None

[web_interface]
enable = True
port = 8082

[cmd_interface]
enable = True
```

For other configurations or detailed parameter descriptions, use `bsbgateway manage` and select "Configure" to see all available options with inline help.

### Device definition file

The set of available fields, datatypes and additional information comes from a
"device definition" file. See the `devices` directory here in the repository.
Currently there is a file for my own heater, [broetje_isr_plus.json](devices/broetje_isr_plus.json), that you can use as starting point. Download and modify it with your editor of
choice.

**Some words of caution**

The list of fields in `broetje_isr_plus.json` was gathered mostly from bus-sniffing my own heating system. In the meantime, the guys at the [BSB_LAN](https://github.com/fredlcore/BSB-LAN) project did an incredible job of gathering this information for hundreds of devices.

As it turns out, there is no real standardization of the device data. **The parameters available differ in meaning, telegram structure and scope significantly**, sometimes even within the same controller model, but across different firmware versions. The big issue here is that one telegram structure might work on a different heater without an issue, but the conversion factor might be 2 instead of 1, 5 instead of 10 or vice versa or something completely different. While this will not immediately damage your heating system, **it can make it run very inefficiently or strain the components**, and you might not even notice where the problem comes from, because, on the web-interface, it still says that the minimum break betweek burner starts is 10 minutes, whereas your heater actually thinks of the same value as 1 minute, for example. ([More information](https://github.com/fredlcore/BSB-LAN/discussions/482))

So, please check all fields of interest against *your* device. Compare what bsbgateway tells you with what you see on the local control panel. That applies especially if you intend to set data and not only monitor it. Use the [dump](https://github.com/loehnertj/bsbgateway/blob/master/doc/cmdline.md#sniffing-the-bus) command for sniffing, and edit your device json file accordingly. 

**'nuff said...**

To get the necessary information, scroll through the menus on your heater and
dump the traffic in the command interface (using `dump on` command). (This might get easier in the future...)

Once you have the device file ready, put it alongside `bsbgateway.ini`
(recommendation: as `~/.config/bsbgateway/my_name.json`). In the configuration,
put the file name without extension (e.g. `my_name`) as "Gateway / Device"
setting.

## Running in terminal

Choose "run" in the management menu, or run `bsbgateway` without parameters. It
will log messages in the terminal.

You should now be able to access the [Web interface](doc/web.md) as well as
enter [Commands](doc/cmdline.md) in the terminal. If things don't work as expected, check the [Troubleshooting](doc/troubleshooting.md) section.

## Installing as system service

Once the program works as you like, you will probably want it to start
automatically and run in the background. For this, you can install it as systemd
service. Run `bsbgateway manage` and choose "Install service".

* This will prompt you for the sudo password.
* The service will run `bsbgateway` from the location and with the user account that are currently active. If you are using a local venv, moving it will break the service.
* On success, you should see a message like "Status:Running".

You can view log messages using `journalctl -u bsbgateway.service`.

Using the management mode, you can also restart and uninstall the service.

Look in [manage.py](src/bsbgateway/manage.py) if you want to know the exact commands that are executed.


## More documentation

 * **[Commandline Interface](doc/cmdline.md)** - Query fields, set values, sniff the bus
 * **[Web Interface](doc/web.md)** - Browser-based control and monitoring
 * **[MQTT Interface](doc/mqtt.md)** - for interfacing with Home Assistant
 * **[Logging](doc/logging.md)** - Data logging with configurable intervals
 * **[Protocol Reference](doc/protocol.md)** - BSB protocol details
 * **[Hardware](doc/hardware.md)** - Adapter circuit specifications
 * **[TCP Bridging](doc/bsb2tcp.md)** - how to expose the bus via TCP
 * **[API & Advanced usage](doc/api.md)** - Programmatic access, custom modules, TCP bridging
 * **[Troubleshooting](doc/troubleshooting.md)** - Common issues and solutions

## Getting Help

If something doesn't work:

1. Run with verbose logging: `bsbgateway manage` → "Configure" → enable debug logging
2. Use `dump on` in the command interface to monitor bus traffic
3. Check the [Troubleshooting guide](doc/troubleshooting.md)
4. Contact me via Github.

## Acknowledgements

This project would not exist without the initial reverse-engineering done by
[Niobos](http://blog.dest-unreach.be/2012/12/14/reverse-engineering-the-elco-heating-protocol).

Lots of work was done by the guys at
[mikrocontroller.net](https://www.mikrocontroller.net/topic/218643).

I got lots of useful advice and information from fredlcore, the mastermind
behind [BSB-LAN](https://github.com/fredlcore/BSB-LAN). His project is more
awesome than mine. Seriously.

As of v1.1, this project includes a modified fork of
[ha-mqtt-discoverable](https://github.com/unixorn/ha-mqtt-discoverable). All
files of the fork are distributed under the original Apache-2.0 license.


## Changelog

Significant modernization happened in 2026.

Planned:

* Test correct reading+writing of all datatypes with actual device
* Add "edit-model" mode with automatic sniffing + adding of fields

(version 1.2 @ 2026-02-23)

* Device JSON format: Simplified string representation + default enums. See https://github.com/loehnertj/bsbgateway/issues/39#issuecomment-4070064072.

(version 1.1 @ 2026-02-23)

* Home Assistant-compatible MQTT endpoint. To this end, a custom version of
  ha_mqtt_discoverable is now "vendored", which uses builtin dataclasses instead
  of pydantic.
* optional per-module loglevel adjustment
* improved error handling
* stricter telegram validity checking (length check)
* internal refactoring (define ConsumerBase class)

(version 1.0 @ 2026-01-31)

* Do not configure in `.py` files anymore (config.py, "device".py). Instead, use ini / json files.
* Completely replace device model and packet reader/writer code.
* Replaced near-dead web.py framework by Flask / Jinja2.
* Add support for all datatypes (esp. date/time input) to web interface.
* Add TCP forwarder and TCP adapter modules.
* Refactor Core code, decouple modules and introduce welldefined interfaces.
* Management mode (`bsbgateway manage`) for interactive configuration and installation as service.
* Proper packaging, using `pyproject.toml` 


