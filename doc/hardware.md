# Bsb Interface hardware

**Preface: The circuit documented here is not recommended for reuse. It connects the Protective Earth (GND) wire of the bus to the "-15V wire" of the RS232 plug. That means that it will fail, possibly destructively, if your RS232 GND is connected to PE (i.e. the power line "ground" contact).**

**Please use a circuit with proper galvanic isolation, i.e. a 2-way optocoupler.**

You can find lots of info and examples here: http://www.mikrocontroller.net/topic/218643.

## BSB hardware layer in short

The `BSB`, a.k.a. `LPB` (Local process bus) is a 2-wire, unipolar voltage bus. While the bus is free, it is at +15V level. Voltages above 8V count as logic 0, below 7V as logic 1.

Besides of the "wrong" voltage levels, the bus protocol is compatible with RS232, 4800 baud, odd parity, 1 stop bit.

Collision detection is done by "CSMA". I.e. devices should never begin sending as long as someone else is sending. When the bus is free, each device that wants to send waits for a random amount of time before it begins sending. As soon as someone begins sending, other devices with pending data suspend their timers and resume them when the bus is free again.

## My circuit

Schematic: [PNG](broetje_interface.sch.svg.png), [EESchema .sch](broetje_interface.sch)

I made this from parts that were lying around, so it has some kinks mentioned below.

There are three basic functional units:

 * The potentiometer `RV1` and LM556N `IC1A` convert the bus voltage level into RS232 levels. All bits are inverted, which is corrected in software. LED `D2` indicates when there is traffic on the bus.
 
 * The lower right part (`R4`, `R5`, `Q2`, `C2`, `C3`, `IC1B`) is a retriggerable monoflop, which is triggered each time there is traffic on the bus. It changes the `CTS` state, indicating that the bus is busy and sending should be delayed. The software will wait for 5ms before trying again. Note that the CTS state is inverted, which is again corrected in software.
 
 * The part at the left (`R1`, `Q1`, `D1`, `R2`) is the sending part. The transistor short-circuits the bus for each 1 bit. The red diode indicates when the circuit is sending.
 
The RTS and DTR pins are used for power supply. Since the RS232 is symmetric, that means that the GND (from device, `P1`) is connected to the negative level of the RS232 (`P2`).
