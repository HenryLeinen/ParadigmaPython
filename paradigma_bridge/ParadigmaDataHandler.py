#!/usr/bin/env python3

import logging
import serial
import logging
import asyncio
import time
import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
import paho.mqtt.client as mqtt
from typing import Dict, Optional, Iterable, Callable
from paradigma_bridge.RegisterHandler import RegisterHandler as RegisterHandler

log = logging.getLogger(__name__)


PERIODIC_TASK_TIME	= 300 # seconds

''' 0x0A: Response codes from Paradigma hinting at the payload  meaning'''
RET_MESSAGE_RESPONSE_START_MONITORING = 0x14
RET_MESSAGE_RESPONSE_STOP_MONITORING = 0x15
RET_MESSAGE_RESPONSE_START_READ_VERSION = 0x16
RET_MESSAGE_RESPONSE_STOP_READ_VERSION = 0x17
RET_MESSAGE_RESPONSE_WRITE_MEMORY = 0x1D
''' 0xFC: Broadcast contents'''
RET_BROADCAST = 0x0C
''' 0xFD: Responses with content from requests'''
RET_MESSAGE_CONTENT_READ_MEMORY = b'\x0C\x03'
RET_MESSAGE_VERSION_INFO = 0xAA
''' Internal message indicators'''
DATASET1 = 0x01
DATASET2 = 0x02
CONFIRM_START_MONITORING = 0x14
CONFIRM_STOP_MONITORING = 0x15
CONFIRM_START_READ_VERSION = 0x16
CONFIRM_STOP_READ_VERSION = 0x17
CONFIRM_WRITE_MEMORY = 0x1D
MEMORY = 0xFD
VERSION_INFO = 0xAA
UNKNOWN_CONFIRMATION_RESPONSE = 0x0A
BROADCAST_UNKNOWN_DATASET = 0xFF




# -------------------------------
# Failure Handling Exceptions
# -------------------------------
class ParadigmaError(Exception):
	pass

class ProtocolError(ParadigmaError):
	pass

class ChecksumError(ProtocolError):
	pass

class PayloadLengthError(ProtocolError):
	pass

class UnknownMessageError(ProtocolError):
	pass

class SerialCommunicationError(ParadigmaError):
	pass

class MqttCommunicationError(ParadigmaError):
	pass




# -------------------------------
# Events
# -------------------------------
@dataclass
class TimerTick:
	pass

@dataclass
class MqttCommand:
	topic: str
	payload: str

@dataclass
class SerialFrameReceived:
	cmd: int
	payload: bytes

@dataclass
class LogEvent:
	text: str

@dataclass
class StartMemoryWatchEvent:
	start_address: int
	length: int
	frequency_s: int

@dataclass
class StopMemoryWatchEvent:
	start_address: int
	length: int | None = None


# -------------------------------
# Actions
# -------------------------------
@dataclass
class SendSerial:
	request: bytes
	payload: bytes

@dataclass
class PublishMqtt:
	topic: str
	payload: str

@dataclass
class LogMessage:
	text: str

@dataclass
class StartMemoryWatch:
	start_address: int
	length: int
	frequency_s: int

@dataclass
class StopMemoryWatch:
	start_address: int
	length: int | None = None


class ParadigmaMessageParser:
	def __init__(self):
		# Map for Betriebsmodes
		self.modes = { 
				'0': "Programm 1",
		                '1': "Programm 2",
		                '2': "Programm 3",
		                '3': "Dauernd Heizen",
		                '4': "Dauernd Komfort",
		                '5': "Dauernd Absenken",
		                '6': "Sommerbetrieb",
		                '7': "Aus",
		                '8': "Party",
		                '11': "Urlaub" }

		self.reverse_modes = {}	# will be generated
		for k, v in self.modes.items():
			self.reverse_modes[str(v)] = k

		self.errorcodes = {  
				'-1': "OK",
		                '0': "STB angesprochen",
		                '2': "Keine Flammbildung",
		                '12': "Stoerung PFA keine Kommunikation",
		                '18': "Kesseltemperatur zu hoch",
		                '19': "Ruecklauftemperatur zu hoch",
		                '28': "Brennergeblaese laeuft nicht",
		                '29': "Brennergeblaese schaltet nicht ab",
		                '31': "Kurzschluss Kesselfuehler",
		                '32': "Kurzschluss Ruecklauffuehler",
		                '35': "Kurzschluss Rauchgasfuehler",
		                '40': "Unterbrechung Kesselfuehler",
		                '43': "Rauchgastemperatur zu hoch",
		                '44': "Rauchgastemperatur im Nocmalbetrieb zu niedrig",
		                '50': "Brandschutzklappe schliesst nicht",
		                '51': "Brandschutzklappe oeffnet nicht",
		                '52': "Einschubschnecke schaltet nicht ein",
		                '53': "Einschubschnecke schaltet nicht aus",
		                '54': "Zuendung schaltet nicht ein",
		                '55': "Zuendung schaltet nicht aus",
		                '56': "Ueberhitzung der Motoren",
		                '57': "Ueberwachung Temperaturschalter",
		                '59': "Max. Anzahl der Fuellversuche ueberschritten",
		                '60': "Fehler Endschalter der Brandschutzklappe"
		        }
		self.regs = RegisterHandler()
		pass

	# -------------------------------
	# Conversion Functions
	# -------------------------------
	def LookupMode(self, mode: str):
		try:
			return self.reverse_modes[mode]
		except Exception as exc:
			log.error(f"Failed to lookup Betriebsmode : {mode}")
		return None



	def _cvtToUInt(self, data, idx, len):
		return int.from_bytes(data[idx:idx+len], byteorder="big", signed=False)

	def _cvtToInt(self, data, idx, len):
		return int.from_bytes(data[idx:idx+len], byteorder="big", signed=True)

	def _cvtToStoercode(self, data, idx):
		stoercode = self._cvtToInt(data, idx, 2)
		return str(stoercode) + ": " + self.errorcodes[str(stoercode)]

	def _cvtToTemperature(self, data, idx):
		return int.from_bytes(data[idx:idx+2], byteorder="big", signed=True) / 10.0

	def _cvtToBetriebsart(self, data, idx):
		betriebsart = self._cvtToUInt(data, idx, 1)
		return self.modes[str(betriebsart)]



	''' Error handling to ensure payload has the right length '''
	def require_payload_length(self, payload: bytes, minimum: int, context: str) -> None:
		if len(payload) < minimum:
			raise PayloadLengthError(
				f"{context}: payload too short, expected at least {minimum} bytes, got {len(payload)}"
			)


	def parseMemory(self, addr, len, data):
		elements = []
		while len>0:
			df = self.regs.get_definition_by_address(addr)
			if df.decoder:
				val = df.decoder(data[0:df.length])
			else:
				print (f"MISSING DECODER for {df.name}")
				log.error (f"MISSING DECODER for {df.name}")
				val = int.from_bytes(data[0:df.length], "big")
			print (f"Setting {df.name} to value {val}, from {data}")
			elements.append((df.name, val))
			len -= df.length
			addr += df.length
			data = data[df.length:]
		return elements

	def parseDataset1(self, ds):
		base = "homie/Paradigma/"
		elements = []
		elements.append((base+"Fuehler/Aussentemperatur",	self._cvtToTemperature(ds, 4)))
		elements.append((base+"Warmwasser/Temperatur", 		self._cvtToTemperature(ds, 6)))
		elements.append((base+"Kessel/Vorlauf", 		self._cvtToTemperature(ds, 8)))
		elements.append((base+"Kessel/Ruecklauf",		self._cvtToTemperature(ds,10)))
		elements.append((base+"Heizkreis/Raumtemperatur",	self._cvtToTemperature(ds,12)))
#		elements.append((base+"Heizkreis_1/Raumtemperatur",	self._cvtToTemperature(ds,14)))
		elements.append((base+"Heizkreis/Vorlauftemperatur",	self._cvtToTemperature(ds,16)))
#		elements.append((base+"Heizkreis_1/Vorlauftemperatur",	self._cvtToTemperature(ds,18)))
		elements.append((base+"Heizkreis/Ruecklauftemperatur",	self._cvtToTemperature(ds,20)))
#		elements.append((base+"Heizkreis_1/Ruecklauftempratur",	self._cvtToTemperature(ds,22)))
		elements.append((base+"Puffer/Oben",			self._cvtToTemperature(ds,24)))
		elements.append((base+"Puffer/Unten",			self._cvtToTemperature(ds,26)))
		elements.append((base+"Kessel/Zirkulationstemperatur",	self._cvtToTemperature(ds,28)))
		return elements

	def parseDataset2(self, ds):
		base = "homie/Paradigma/"
		elements = []
		elements.append((base+"Heizkreis/Raumsoll",		self._cvtToTemperature(ds, 0)))
#		elements.append((base+"Heizkreis_1/Raumsoll",		self._cvtToTemperature(ds, 2)))
		elements.append((base+"Heizkreis/Vorlaufsoll",		self._cvtToTemperature(ds, 4)))
#		elements.append((base+"Heizkreis_1/Vorlaufsoll",	self._cvtToTemperature(ds, 6)))
		elements.append((base+"Warmwasser/Soll",		self._cvtToTemperature(ds, 8)))
		elements.append((base+"Puffer/Soll",			self._cvtToTemperature(ds,10)))
		elements.append((base+"Kessel/Betriebsstunden",		self._cvtToUInt(ds,14,4)))
		elements.append((base+"Kessel/Starts",			self._cvtToUInt(ds,18,4)))
		elements.append((base+"Kessel/StoercodeText",		self._cvtToStoercode(ds,22)))
		elements.append((base+"Kessel/Stoercode",		self._cvtToInt(ds,22,2)))
		elements.append((base+"Fuehler/Stoercode",		self._cvtToInt(ds,24,1)))
		elements.append((base+"Heizkreis/Betriebsart",		self._cvtToBetriebsart(ds,25)))
#		elements.append((base+"Heizkreis_1/Betriebsart",	self._cvtToUInt(ds,27,1)))
		elements.append((base+"Heizkreis/Niveau",		self._cvtToUInt(ds,26,1)))
#		elements.append((base+"Heizkreis_1/Niveau",		self._cvtToUInt(ds,28,1))
		elements.append((base+"Heizkreis/Leistung",		self._cvtToUInt(ds,29,1)))
#		elements.append((base+"Heizkreis_1/Leistung",		self._cvtToUInt(ds,30,1)))
		return elements

	def parseVersion(self, payload) -> str:
		v1_high = int(payload[1])
		v1_low  = int(payload[0])
		v2_high = int(payload[3])
		v2_low  = int(payload[2])
		return str(f"SystaComfort V{v2_high}.{v2_low} / Steuerung V{v1_high}.{v1_low}")

	def parseMessage(self, cmd, payload):
		try:
			''' COnfirmation response '''
			if cmd == 0x0A:
				self.require_payload_length(payload, 1, "confirmation response")

				if payload[0] == RET_MESSAGE_RESPONSE_START_MONITORING:
					return (CONFIRM_START_MONITORING, payload)
				elif payload[0] == RET_MESSAGE_RESPONSE_STOP_MONITORING:
					return (CONFIRM_STOP_MONITORING, payload)
				elif payload[0] == RET_MESSAGE_RESPONSE_START_READ_VERSION:
					return (CONFIRM_START_READ_VERSION, payload)
				elif payload[0] == RET_MESSAGE_RESPONSE_STOP_READ_VERSION:
					return (CONFIRM_STOP_READ_VERSION, payload)
				elif payload[0] == RET_MESSAGE_RESPONSE_WRITE_MEMORY:
					return (CONFIRM_WRITE_MEMORY, payload)

				raise UnknownMessageError(f"unknwon confirmation response {payload[0]:02X}")

			# Broadcast response
			elif cmd == 0xFC:
				self.require_payload_length(payload, 2, "broadcast response")

				if payload[0] != RET_BROADCAST:
					raise UnknownMessageError(
						f"Invalid broadcast marker: expected 0x{RET_BROADCAST:02X}, got 0x{payload[0]:02X}"
					)

				if payload[1] == 0x01:
					return (DATASET1, payload[2:])
				elif payload[1] == 0x02:
					return (DATASET2, payload[2:])

				return (BROADCAST_UNKNOWN_DATASET, payload[2:0])

			#  Read Memory Response
			elif cmd == 0xFD:
				self.require_payload_length(payload, 1, "content response")

				if payload[0:2] == RET_MESSAGE_CONTENT_READ_MEMORY:
					self.require_payload_length(payload, 6, "read memory response")

					addr = int(payload[2])*256 + int(payload[3])
					length = int(payload[4])
					self.require_payload_length(payload, 5 + length, "read memory payload")

					return (MEMORY, [addr, length, payload[5:]])
				elif payload[0] == RET_MESSAGE_VERSION_INFO:
					self.require_payload_length(payload, 5, "version info")
					return (VERSION_INFO, payload[1:])

				raise UnknownMessageError(f"Unknown 0xFD reaponse {payload.hex(':')}")

			raise UnknownMessageError(f"Unknown command byte {cmd:02X}")

		except ProtocolError:
			raise

		except Exception as exc:
			raise ProtocolError(f"Failed to parse message cmd=0x{cmd:02X} payload={payload.hex(':')}") from exc

