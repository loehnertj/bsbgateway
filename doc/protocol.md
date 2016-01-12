# BSB protocol

Disclaimer: All that is written here was found out by reverse engineering. It may or may not be valid for your particular device.

## Credits

Lots of work was done by the guys at [mikrocontroller.net](https://www.mikrocontroller.net/topic/218643).

The packet structure was deciphered by one Niobos here: http://blog.dest-unreach.be/2012/12/14/reverse-engineering-the-elco-heating-protocol

The value formats (except for temperature values) were deciphered by myself. They may be universal or only for the Broetje ISR, I don't know.


## Packet structure

Packets are at least 10 bytes long. The longest packets I have seen so far were 26 bytes (16 payload bytes), so that may be the upper limit. Example packet: `DC 80 0A 0E 07 05 3D 05 6F 00 FD 8E F5 4A`

The structure is as follows:

Name | Length in bytes | example | Remarks
Magic byte | 1 | `DC` | always `DC`
Source address | 1 | `80` | XORed with `80` (in example, src is device `0`)
Destination address | 1 | `0A` | 
Length of packet | 1 | `0E` | total length including bytes before and CRC
Telegram type | 1 | `07` | `inf` (2), `set` (3), `ack` (4), `get` (6), or `ret` (7)
Field ID | 4 | `05 3D 05 6F` | For `get` and `set` packet type, first and second byte (e.g. `05` and `3D`) are swapped.
Payload | variable 0 - 16? | `00 FD 8E` |
CRC | 2 | `F5 4A` | CRC16-CCITT (XModem)

### Address

Address 0 is usually the base device (in home setups). The LCD control panel is 0A for my device, which seems to be a common choice.

Address 7F is used for broadcasting. Addresses >= 80 may be illegal.

### Telegram type

 * `inf` packets ("info") seem only to be used for broadcasts, e.g. regular timestamp and temperature sensor packets.
 * `set` packets are used to change values. They contain the new value as payload and are answered by `ack` without payload.
 * `get` packets are used to retrieve values. They contain no paylad and are answered by `ret` with the current value as payload.

### Field ID

I currently don't know much about the field id. At first glance they seem to map 1:1 to the "display IDs" (4-digit numbers in the LCD panel), but so far I found no rule for mapping one to the other. 

I found cases where two field ids differing only in the last bit return the same value. The first two bytes are often the same for most fields in one menu (e.g. 0x313D in "Trinkwasser", 0x053D in "Status"). So the field id could encode further information or flags.

### Payload

There is a payload in `inf`, `set` and `ret` packets, but not in `ack` and `get` packets. For one field, the payload length is always the same. See below for detailed discussion of datatypes.


## Values

There are basic 8-, 16- and 32-bit integer types as well as some special types (time, schedule, others). There may be more that I did not see so far.

There is a distinction between nullable and non-nullable fields, which is important when setting values.

### Int8

An `int8` payload consists of two bytes: `<flag>` (1B), `<value>` (1B) e.g. `00 14`.

The value is a simple byte value. So far I don't know if it is signed or unsigned. This might be field specific.

#### Flag

In a **`ret` telegram**, flag `00` indicates a "normal" value, `01` a null value. In the latter case, the `<value>` byte should be ignored.

In a **`set` telegram**, the flag is set to:

 * `01` when setting the value of a non-nullable field;
 * `05` when setting a value for a nullable field;
 * `06` when setting a nullable field to NULL (in this case, the `<value>` byte will be ignored).
 
### Choice

Choice fields are simply `int8` fields with fixed meanings for each value (i.e. Enums if you know C). The possible values can be found in the [Systemhandbuch](https://www.mikrocontroller.net/attachment/118129/systemhandbuch_isr.pdf), at least if the field is documented. I am looking at you, No. 8009.

### Int16

The `int16` payload consists of three bytes: `<flag>` (1B), `<value>` (2B) e.g. `00 FD 8E`.

The flag works the same as for `int8`.

The value is big-endian and (for all fields I saw so far) signed. It is common to find fix-point values, i.e. the `int16` value has to be divided by a fixed number to get the "physical" value.

### Temperature

All temperature fields I saw so far are `int16` fields with divisor 64. E.g. FD 8E = -626 (dec), then the temperature is (-626/64.) = -9.78 °C.

### Int32

The `int32` payload consists of five bytes: `<flag>` (1B), `<value>` (4B) e.g. `00 00 4C F5 90`.

The flags probably works the same as for `int8`.

The value is big-endian. A common use is for operating time counters, where the value is the operating time in seconds.

### Time

Time fields encode a time in three bytes: `<flag>` (1B), `<hour>` (1B), `<minute>` (1B) e.g. `00 06 1E` (06:30).

The flag works the same as for `int8`.

The LCD panel allows only 10-minute increments. Values inbetween may or may not be legal.

### Schedule

Schedule fields encode up to three time intervals for 1 day. They like to come in bunches of 7 (meaning monday..sunday).

They have 12 bytes: `hh1 mm1 hh2 mm2 ... hh6 mm6`. The active intervals are then hh1:mm1-hh2:mm2, hh3:mm3-hh4:mm4, hh5:mm5-hh6:mm6.

Unused intervals are set by the sequence `80 00 00 00`. (My device then returns `98 00 18 00` when `get`ting the value.)

The LCD panel sorts unused intervals to the end, sorts by start time and merges overlapping intervals.

*So far, the schedule type is not implemented in BsbGateway.*