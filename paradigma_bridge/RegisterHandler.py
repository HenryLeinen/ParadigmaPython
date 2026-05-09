#!/usr/bin/env python3

import logging
import time
import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from typing import Dict, Optional, Iterable, Callable





def decode_temperature(data:bytes) -> float:
	return int.from_bytes(data, "big") / 10.0

def decode_date(data:bytes) -> date:
	days= int.from_bytes(data, "big")
	base_date = date(2000,1,1)
	return (base_date + timedelta(days=days)).isoformat()

def decode_uint8(data:bytes) -> int:
	return int.from_bytes(data, "big")

def encode_temperature(temp:float) -> bytes:
	t = int(temp*10.0)
	return t.to_bytes(2, "big")

def encode_date(d:date) -> bytes:
	base_date = date(2000,1,1)
	delta_days = (d-base_date).days
	if delta_days<0:
		raise ValueError("Date is before 2000-01-01")
	return delta_days.to_bytes(2, "big")

def encode_uint8(d:int) -> bytes:
	return d.to_bytes(1, "big")


@dataclass
class RegisterDefinition:
	name: str
	address: int
	length: int
	description: str
	data_dictionary: str
	decoder: Optional[Callable[[bytes], float]] = None
	encoder: Optional[Callable[float, [bytes]]] = None



REGISTER_DEFINITIONS = [
	RegisterDefinition(
		name="Betriebsart HK1",
		address= 0x0002,
		length = 1,
		description = "Betriebsart Heizkreis 1",
		data_dictionary = "0=Programm1, 1=Programm2, 2=Programm3, ..., 8=Aus"
	),
	RegisterDefinition(
		name="Heiztemperatur_HK1",
		address= 0x0005,
		length = 2,
		description = "Heiztempperatur",
		data_dictionary = "In 0.1K",
		decoder = decode_temperature,
		encoder = encode_temperature
	),
	RegisterDefinition(
		name="Komforttemperatur_HK1",
		address= 0x0007,
		length = 2,
		description = "Komforttemperatur",
		data_dictionary = "In 0.1K",
		decoder = decode_temperature,
		encoder = encode_temperature
	),
	RegisterDefinition(
		name="Absenktemperatur_HK1",
		address = 0x0009,
		length = 2,
		description = "Absenktemperatur",
		data_dictionary = "In 0.1K",
		decoder = decode_temperature,
		encoder = encode_temperature
	),
	RegisterDefinition(
		name="Ferienbeginn",
		address = 0x000B,
		length = 2,
		description = "Begin des Ferienprogramms",
		data_dictionary = "In Tagen seit 01.01.2000",
		decoder = decode_date,
		encoder = encode_date
	),
	RegisterDefinition(
		name="Ferienende",
		address = 0x000D,
		length = 2,
		description = "Ende des Ferienprogramms",
		data_dictionary = "In Tagen seit 01.01.2000",
		decoder = decode_date,
		encoder = encode_date
	),
	RegisterDefinition(
		name="Maximale Vorlauftemperatur",
		address = 0x0015,
		length = 2,
		description = "Maximale Vorlauftemperatur",
		data_dictionary = "In 0.1K",
		decoder = decode_temperature,
		encoder = encode_temperature
	),
	RegisterDefinition(
		name="Nachstellzeit",
		address = 0x0018,
		length = 1,
		description = "Nachstellzeit",
		data_dictionary = "min",
		decoder = decode_uint8,
		encoder = encode_uint8
	),
	RegisterDefinition(
		name="Heizgrenze Heizbetrieb",
		address = 0x001D,
		length = 2,
		description="Heizgrenze Heizbetrieb",
		data_dictionary="In 0.1K",
		decoder = decode_temperature,
		encoder = encode_temperature
	),
	RegisterDefinition(
		name="Heizgrenze Absenken",
		address = 0x001F,
		length = 2,
		description = "Heizgrenze Absenken",
		data_dictionary="In 0.1K",
		decoder = decode_temperature,
		encoder = encode_temperature
	)
]


class RegisterHandler:
	'''
	Stores register definitions and raw register values

	Access patterns:
		regs["Heiztemperatur HK1"]	-> return raw bytes
		regs.get_by_address(0x0005)	-> return raw bytes

	writing:
		regs.store(0x0005, b'\\x01\\x05')
	'''
#	def __init__(self, definitions: Iterable[RegisterDefinition]) -> None:
	def __init__(self) -> None:
		self._defs_by_name: Dict[str, REGISTER_DEFINITIONS] = {}
		self._defs_by_address: Dict[int, REGISTER_DEFINITIONS] = {}
		self._values: Dict[int, bytes] = {}

		for reg in REGISTER_DEFINITIONS:
			if reg.name in self._defs_by_name:
				raise ValueError(f"Duplicate register name: {reg.name}")
			if reg.address in self._defs_by_address:
				raise ValueError(f"Duplicate register address: {reg.address}")
			self._defs_by_name[reg.name] = reg
			self._defs_by_address[reg.address] = reg

	def __getitem__(self, register_name: str) -> bytes:
		''' 
		Returns the raw register value as bytes
		Example:
			regs["Heitemperatur HK1"]
		'''
		reg = self._defs_by_name.get(register_name)
		if reg is None:
			raise KeyError(f"Unknown resiger name: {register_name}")

		if reg.address not in self._values:
			raise KeyError(f"No value stored for register: {register_name}")

		return self._values[reg.address]

	def __contains__(self, register_name: str) -> bool:
		reg = self._defs_by_name.get(register_name)
		return reg is not None and reg.address in self._values

	def store(self, address: int, value: bytes | bytearray) -> None:
		'''
		Stores a raw register value by address

		The length must match the register definition exactly
		'''
		reg = self._defs_by_address.get(address)
		if reg is None:
			raise KeyError(f"Unknown register address: 0x{address:04X}")

		raw = bytes(value)

		if len(raw) != reg.length:
			raise ValueError(
				f"Length mistmatch for register '{reg.name}' at 0x{address:04X}: "
				f"expected {reg.length} bytes, got {len(raw)} bytes"
			)

		self._values[address] = raw

	def get_by_address(self, address: int) -> bytes:
		if address not in self._defs_by_address:
			raise KeyError(f"Unknown register address: 0x{address:04X}")
		if address not in self._values:
			raise KeyError(f"No value stored for register at address: 0x{address:04X}")
		return self._values[address]

	def get_definition_by_name(self, register_name: str) -> RegisterDefinition:
		reg = self._defs_by_name.get(register_name)
		if reg is None:
			raise KeyError(f"Unknown regieter name: {register_name}")
		return reg

	def get_definition_by_address(self, address:int) -> RegisterDefinition:
		reg = self._defs_by_address.get(address)
		if reg is None:
			raise KeyError(f"Unknown register address: 0x{address:04X}")
		return reg

	def get_u8(self, register_name: str) -> int:
		raw = self[register_name]
		if len(raw) != 1:
			raise ValueError(f"Register '{register_name}' is not 1 byte long")
		return raw[0]

	def get_u16_be(self, register_name: str) -> int:
		raw = self[register_name]
		if len(raw) != 2:
			raise ValueError(f"Register '{register_name}' is not 2 byte long")
		return int.from_bytes(raw, byteorder="big", signed=False)

	def get_scaled_0_1(self, register_name: str) -> float:
		return self.get_u16_be(register_name) / 10.0
