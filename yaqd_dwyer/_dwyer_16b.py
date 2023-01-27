__all__ = ["DwyerTemperatureController"]

import asyncio
from typing import Dict, Any, List
import math

import serial  # type: ignore
import minimalmodbus  # type: ignore

from yaqd_core import HasLimits, HasPosition, UsesSerial, UsesUart, IsDaemon


def int2temp(value):
    if value >= 2**15:
        value -= 2**16
    return value / 10


def temp2int(value):
    value = int(value * 10)
    if value < 0:
        value += 2**15
    return value


class Dwyer16B(HasLimits, HasPosition, UsesUart, UsesSerial, IsDaemon):
    _kind = "dwyer-16b"

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        self._instrument = minimalmodbus.Instrument(
            port=self._config["serial_port"], slaveaddress=self._config["modbus_address"]
        )
        self._instrument.serial.baudrate = self._config["baud_rate"]
        self._instrument.serial.bytesize = self._config["byte_size"]
        self._instrument.serial.stopbits = self._config["stop_bits"]
        self._instrument.serial.parity = self._config["parity"]
        self._instrument.handle_local_echo = self._config["modbus_handle_echo"]
        # ensure that control method is PID
        self._ramping = False
        self._instrument.write_register(0x1005, 0)
        # units
        if self._instrument.read_bit(0x0811):
            self._units = "deg_C"
        else:
            self._units = "deg_F"
        # limits
        self._state["hw_limits"][0] = int2temp(self._instrument.read_register(0x1003))
        self._state["hw_limits"][1] = int2temp(self._instrument.read_register(0x1002))
        # normalize patterns
        self._instrument.write_register(0x1030, 0)  # start pattern is pattern zero
        self._instrument.write_register(0x1060, 8)  # program ends after pattern zero
        for i in range(8):
            self._instrument.write_register(0x2000 + i, 0)  # set points for pattern zero
            self._instrument.write_register(0x2080 + i, 0)  # execution time for pattern zero

        # TODO: default in toml, yaq property
        self._state["rate"] = 1  # degrees per minute

    def direct_serial_write(self, message: bytes):
        self._instrument.serial.write(message)

    def get_ramp_time(self) -> float:
        return self._state["ramp_time"]

    def get_ramp_time_limits(self) -> List[float]:
        return [0.0, 900.0]

    def get_ramp_time_units(self) -> str:
        return "min"

    def _set_position(self, position: float):
        if self._state["ramp_time"] == 0:
            self._instrument.write_register(0x1005, 0)
            self._instrument.write_register(0x1001, temp2int(position))
            return
        current_temperature = self._state["position"]
        # do not soak at current temperature
        self._instrument.write_register(0x2080, 0)
        # start at current temperature
        self._instrument.write_register(0x2000, current_temperature)
        # reach goal temperature at time
        self._instrument.write_register(0x2081, int(self._state["ramp_time"]))
        self._instrument.write_register(0x2001, temp2int(position))  # goal temperature
        self._instrument.write_register(0x2082, 900)  # wait "forever" ...
        self._instrument.write_register(0x2002, temp2int(position))  # ... at goal temperature
        # launch
        self._instrument.write_register(0x1005, 3)
        self._instrument.write_bit(0x0814, 1)  # control RUN
        self._instrument.write_bit(0x0815, 0)  # program RUN
        self._instrument.write_bit(0x0816, 0)  # program UNPAUSE
        self._ramping = True

        def callback():
            self._ramping = False

        self._loop.call_later(delay=self._state["ramp_time"] * 60, callback=callback)

    def set_ramp_time(self, ramp_time: float) -> None:
        self._state["ramp_time"] = ramp_time

    async def update_state(self):
        """Continually monitor and update the current daemon state."""
        while True:
            try:
                if self._ramping:
                    self._busy = True
                else:
                    self._busy = False
                    self._instrument.write_register(0x1005, 0)
                    if not math.isnan(self._state["destination"]):
                        self._instrument.write_register(
                            0x1001, temp2int(self._state["destination"])
                        )
                registers = self._instrument.read_registers(0x1000, 5)
                self._state["position"] = registers[0] / 10
                self._state["destination"] = registers[1] / 10
                await asyncio.sleep(0.25)
            except minimalmodbus.LocalEchoError:
                continue
            except minimalmodbus.InvalidResponseError:
                continue
            except minimalmodbus.NoResponseError:
                continue
            except minimalmodbus.SlaveReportedException:
                continue
