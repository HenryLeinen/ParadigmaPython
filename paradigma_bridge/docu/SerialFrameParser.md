# class SerialFrameParser

## Description
Class SerialFrameParser encapsulates the interpretation of message packets from Paradigma Pelletti read via a serial interface.

## Message Frame Structure
The general structure of a Paradigma message is as follwos:

<Command> --> <Length> --> <Databyte_1>..<Databyte_LEN> --> <Checksum>

### Command byte
A command can be one of the values :
0Ah
FCh
FDh

### Length byte
The length byte specifies the number of data bytes contained in this message

### Data bytes
This is the payload of the message

### Checksum
The checksum is the sum of all databytes, the length byte and the command byte.

## Class Member
The function feed shall be called for each byte received over the serial interface.
Each byte will be processed by the internal state machine. The state machine can recover from errors.
One error can be that the start byte is not recognizes, this will reset the state machine.
The second error is a checksum error in which case the received message will be discarded and the state machine will also be reset.

Upon successful frame reception the callback function which was provided with the constructor will be called providing the start byte as well as the payload.


