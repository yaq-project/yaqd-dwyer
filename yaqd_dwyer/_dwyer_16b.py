__all__ = ["DwyerTemperatureController"]

import asyncio
from typing import Dict, Any, List

import serial  # type: ignore
import minimalmodbus  # type: ignore

from yaqd_core import HasLimits, HasPosition, UsesSerial, UsesUart, IsDaemon


def int2temp(value):
    if value >= 2**15:
        value -= 2**16
    return value / 10


def temp2value(value):
    value = int(value * 10)
    if value < 0:
        value += 2**15
    return value


class Dwyer16B(HasLimits, HasPosition, UsesUart, UsesSerial, IsDaemon):
    _kind = "dwyer-16b"

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        self._instrument = minimalmodbus.Instrument(port=self._config["serial_port"],
                                                    slaveaddress = self._config["modbus_address"])
        self._instrument.serial.baudrate = self._config["baud_rate"]
        self._instrument.serial.bytesize = self._config["byte_size"]
        self._instrument.serial.stopbits = self._config["stop_bits"]
        self._instrument.serial.parity = self._config["parity"]
        self._instrument.handle_local_echo = self._config["modbus_handle_echo"]
        # ensure that control method is PID
        self._instrument.write_register(0x1005, 0)
        # units
        if self._instrument.read_bit(0x0811):
            self._units = "deg_C"
        else:
            self._units = "deg_F"
        # limits
        self._state["hw_limits"][0] = int2temp(self._instrument.read_register(0x1003))
        self._state["hw_limits"][1] = int2temp(self._instrument.read_register(0x1002))

    def direct_serial_write(self, message: bytes):
        self._instrument.serial.write(message)

    def _set_position(self, position: float):
        value = int(position * 10)
        self._instrument.write_register(0x1001, value)

    async def update_state(self):
        """Continually monitor and update the current daemon state."""
        # If there is no state to monitor continuously, delete this function
        while True:
            try:
                self._busy = False
                registers = self._instrument.read_registers(0x1000, 5)
                self._state["position"] = registers[0] / 10
                self._state["destination"] = registers[1] / 10
                await asyncio.sleep(0.25)
            except minimalmodbus.LocalEchoError:
                continue
