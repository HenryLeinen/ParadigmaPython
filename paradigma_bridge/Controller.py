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
from paradigma_bridge.SerialFrameParser import SerialFrameParser
from paradigma_bridge.ParadigmaDataHandler import ParadigmaMessageParser





''' Serial commands sent to paradigma '''
CMD_READ_MEMORY 	= b'\x1c\x0c\x03'
CMD_START_MONITORING	= b'\x14'
CMD_STOP_MONITORING	= b'\x15'
CMD_START_READ_VERSION	= b'\x16'
CMD_STOP_READ_VERSION	= b'\x17'
CMD_WRITE_MEMORY	= b'\x1d\x0c\x11\x53\x45\x54'
CMD_WRITE_CLOCK		= b'\x1d\x0c\x09\x55\x48\x52'
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

class Controller:
	def __init__(self, ser, log):
		self.ser = ser
		self.log = log
		# Setup the MQTT client
		self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
		self.client.on_connect = self._onConnect
		self.client.on_disconnect = self._onDisconnect
		self.client.on_message = self._onMessage
		self.client.connect("leinihomesrv.local", 1883, 60)
		self.client.user_data_set([])
		self.client.loop_start()
		self.client.reconnect_delay_set(10, 600)
		self.client.subscribe("paradigma/heating/#")
		# Setup internal variables
		self.PERIODIC_TASK_TIME	= 300 # seconds
		self.dataset1_received = False
		self.dataset2_received = False
		self.awaiting_response = False
		self.awaiting_version_info = False

		self.event_queue = asyncio.Queue()
		self.serial_tx_queue = asyncio.Queue()

		self.running = True

		self.parser = SerialFrameParser(self._on_serial_frame, log)

		self.msg_parser = ParadigmaMessageParser(log)

		self.last_query_ts = 0.0

		self.memory_watch_tasks = {}



	# -----------------------------------
	# MQTT Client callbacks
	# -----------------------------------
	def _onConnect(self, client, userdata, message, rc, properties):
		print("MQTT: Successfully connected to MQTT broker")
		self.log.info("MQTT: Successfully connected to MQTT broker")

	def _onDisconnect(self,client, userdata, disconnect_flags, rc, properties):
		print("MQTT: Disconnection from MQTT broker")
		self.log.debug("MQTT: Disconnected from MQTT broker !!!")

	def _onMessage(self, client, userdata, message):
		try:
			payload = message.payload.decode("utf-8").strip()
		except UnicodeDecodeError:
			log.error("Invalid MQTT payload encoding on topic %s", message.topic)
			return
		self.on_mqtt_message(topic=message.topic, payload=payload)


	def subscribe_mqtt(self):
		self.client.connect("leinihomesrv.local", 1883, 60)
		self.client.user_data_set([])
		self.client.subscribe("paradigma/heating/#")

	def publish_mqtt(self, topic, payload):
		if not self.client.is_connected():
			self.client.reconnect()
			self.log.error("MQTT: was disconnected when publishing. Tried reconnect!")
		self.client.publish(topic, payload)

	# -----------------------------------
	# Event producers
	# -----------------------------------
	def _on_serial_frame(self, cmd: int, payload: bytes):
		''' Called by Parser whenever there is a new message received
		    this is synchronous so put_nowait '''
		self.event_queue.put_nowait(SerialFrameReceived(cmd=cmd, payload=payload))

	def on_mqtt_message(self, topic: str, payload: str):
		''' Call this from MQTT callback '''
		self.event_queue.put_nowait(MqttCommand(topic=topic, payload=payload))

	async def periodic_query_task(self):
		while self.running:
			await asyncio.sleep(self.PERIODIC_TASK_TIME)	#e.g. every 5 minutes
			await self.event_queue.put(TimerTick())

	async def serial_reader_task(self):
		while self.running:
			try:
				data = await asyncio.to_thread(self.ser.read, 1)
				if data and len(data) == 1:
					self.parser.feed(data[0])
				else:
					await asyncio.sleep(0.01)

			except serial.SerialException as exc:
				self.log.exception("Serial read error")
				await self.event_queue.put(LogEvent(f"Serial read error: {exc}"))
				await asyncio.sleep(2.0)

			except Exception as exc:
				self.log.exception("Unexpected serial reader error")
				await self.event_queue.put(LogEvent(f"Unexpected serial reader error: {exc}"))
				await asyncio.sleep(1.0)


	async def serial_writer_task(self):
		while self.running:
			msg = await self.serial_tx_queue.get()

			try:
				frame = self._build_frame(msg.request, msg.payload)
				self.log.debug("Serial TX: %s", frame.hex(':'))
				await self.event_queue.put(LogEvent(f"**** Serial TX: {frame.hex(':')}"))
				await asyncio.to_thread(self.ser.write, frame)

			except serial.SerialException as exc:
				self.log.exception("Serial write error")
				await self.event_queue.put(LogEvent(f"Serial write error: {exc}"))

			except Exception as exc:
				self.log.excpetion("Unexpected serial writer error")
				await self.event_queue.put(LogEvent(f"Unexpected serial writer error: {exc}"))

			finally:
				self.serial_tx_queue.task_done()

	async def memory_watch_task(self, start_address: int, length: int, frequency_s: int):
		try:
			while self.running:

				await self.event_queue.put(LogEvent("WATCH TASK TRIGGERED"))
				payload = bytes([(start_address>>8) & 0xFF, start_address&0xFF, length&0xFF])
				await self.serial_tx_queue.put( SendSerial(request=CMD_READ_MEMORY, payload=payload) )
				await asyncio.sleep(frequency_s)

		except asyncio.CancelledError:
			self.log.error ("WATCH TASK CANCELLED")
			raise

		except Exception as e:
			self.log.error (f"WATCH TASK ERROR: {type(e).__name__}: {e}")
			raise


	async def start_memory_watch(self, start_address: int, length: int, frequency_s: int):
		key = (start_address, length)

		old_task = self.memory_watch_tasks.get(key)
		if old_task is not None:
			old_task.cancel()

			try:
				await old_task
			except asyncio.CancelledError:
				pass

		task = asyncio.create_task(
			self.memory_watch_task(
				start_address=start_address,
				length=length,
				frequency_s=frequency_s
			)
		)

		self.memory_watch_tasks[key] = task

		await self.event_queue.put(LogEvent (
			f"Started memory watch: "
			f"address=0x{start_address:04X}, length={length}, "
			f"frequency={frequency_s}s"
		))

	async def stop_memory_watch(self, start_address: int, length: int):
		if length is not None:
			keys = [(start_address, length)]
		else:
			keys = [
				key for keys in self.memory_watch_tasks
				if key[0] == start_address
			]

		for key in keys:
			task = self.memory_watch_tasks.pop(key, None)

			if task is not None:
				task.cancel()

				try:
					await task
				except asyncio.CancelledError:
					pass

				await self.event_queue.put(LogEvent (
					f"Stopped memory watch: "
					f"address=0x{key[0]:04X}, length={key[1]}"
				))

	# -------------------------------
	# Protocol helper
	# -------------------------------
	def _build_frame(self, request: bytes, payload:bytes) -> bytes:
		request = bytes(request)
		payload = bytes(payload)
		length = len(payload)+len(request)
		checksum = (-(0x0a + sum(request) + length + sum(payload))) & 0xFF
		return bytes([0x0a, length]) + request + payload + bytes([checksum])


	# -------------------------------
	# Central control logic
	# -------------------------------
	def handle_event(self, event) -> list[Any]:
		actions = []

		if isinstance(event, TimerTick):
			# periodic request every 5 minutes
			self.log.info("Periodic serial query triggered")
			actions.append(SendSerial(request = CMD_START_MONITORING, payload = []))
			self.last_query = time.time()
			self.awaiting_response = True

		elif isinstance(event, StartMemoryWatchEvent):
			actions.append(
				StartMemoryWatch(
					start_address=event.start_address,
					length=event.length,
					frequency_s=event.frequency_s
				)
			)

		elif isinstance(event, StopMemoryWatchEvent):
			actions.append(
				StopMemoryWatch(
					start_address=event.start_address,
					length=event.length
				)
			)

		elif isinstance(event, LogEvent):
			actions.append(LogMessage(event.text))

		elif isinstance(event, MqttCommand):
			if event.topic == "paradigma/heating/setmode":
				''' check if heating mode exists and convert it to the associated number '''
				self.log.info (f"Handle MQTT event paradigma/heating/setmode Payload {event.payload}")
				val = self.msg_parser.LookupMode(str(event.payload))
				if val == None:
					actions.append(LogMessage(f"Invalid Heating Mode {event.payload}"))
				else:
					mypayload = b'\x00\x02\x01' + int(val).to_bytes(1)
					actions.append(SendSerial(request=CMD_WRITE_MEMORY, payload=mypayload))
					actions.append(LogMessage(f"Sending cmd=0x0A, payload={mypayload}"))
			elif event.topic == "paradigma/heating/gettemperatures":
				self.log.info (f"Handle MQTT event paradigma/heating/gettemperatures Payload {event.payload}")
				mypayload = b'\x00\x05\x06'
				actions.append(LogMessage(f"Sending cmd=0x0A, payload={mypayload}"))
				actions.append(SendSerial(request=CMD_READ_MEMORY, payload=mypayload))
			elif event.topic == "paradigma/heating/settemperatures":
				self.log.info (f"Handle MQTT event paradigma/heating/settemperatures Payload {event.payload}")
#				mypayload = CMD_WRITE_MEMORY + b'\x00\x05\x06' + 
				pass
			elif event.topic == "paradigma/heating/getferien":
				self.log.info (f"Handle MQTT event paradigma/heating/getferien Payload {event.payload}")
				mypayload = b'\x00\x0b\x04'
				actions.append(LogMessage(f"Sending cmd=0x0A, payload={mypayload}"))
				actions.append(SendSerial(request=CMD_READ_MEMORY, payload=mypayload))
			elif event.topic == "paradigma/heating/gettimetable":
				self.log.info (f"Handle MQTT even paraidmga/heating/gettimetable Payload {event.payload}")
				start = -1
				length = 112
				id = int(event.payload)
				if id == 11:
					start = 0x002c
				elif id == 12:
					start = 0x009c
				elif id == 13:
					start = 0x010c
				elif id == 21:
					start = 0x01B2
				elif id == 22:
					start = 0x0222
				elif id == 23:
					start = 0x0292
				elif id == 1:
					start = 0x0317
				elif id == 2:
					start = 0x0387
				else:
					actions.append(LogMessage(f"Unknown Zeitprogramm {id} specified in MQTT {event.topic}"))
					self.log.debug(f"Unknown Zeitprogram {id} specified in MQTT {event.topic}")
				if start != -1:
					mypayload = bytes([start>>8, start&0xff, length&0xff])
					actions.append(SendSerial(request=CMD_READ_MEMORY, payload=mypayload))
					actions.append(LogMessage(f"Sending cmd=0x0A, payload={mypayload}"))

			elif event.topic == "paradigma/heating/update_interval":
				# Set a new frequency for the task
				self.log.info (f"Handle MQTT event paradigma/heating/update_interval Payload {event.payload}")
				update_interval = int(event.payload)
				if update_interval > 15 and update_interval < 300:
					actions.append(LogMessage(f"PERIODIC_TASK_TIME was changed from {self.PERIODIC_TASK_TIME}sec to {update_interval}sec"))
					self.PERIODIC_TASK_TIME = update_interval
				else:
					actions.append("Attribute update_interval not found in MQTT topic")

			elif event.topic == "paradigma/heating/temperatures":
				# Set new temperatures in HEIZKREIS 1
				self.log.info (f"Handle MQTT event paradigma/heating/temperatures Payload {event.payload}")
				required = [ "heizen", "komfort", "absenken"]
				heizen = 18.0
				komfort = 22.0
				absenken = 15.0
				try:
					data = json.loads(event.payload)
					if all(k in data for k in required):
						heizen = float(data["heizen"])
						komfort = float(data["komfort"])
						absenken = float(data["absenken"])
						if heizen > 15.0 and heizen < 25.0 and komfort > 15.0 and komfort < 25.0 and absenken > 5.0 and absenken < 20.0:
							actions.append(LogMessage(f"TODO: change temperatures to : heizen={heizen}, komfort={komfort}, absenken={absenken}!"))
				except json.JSONDecodeError as exc:
					actions.append(LogMessage(f"Failed to decode the payload of paradigma/heating/temperatures : {event.payload}"))
					self.log.error(f"Failed to decode the payload of paradigma/heating/temperatures : {event.payload}")
				pass
			elif event.topic == "paradigma/heating/readmemory":
				self.log.info (f"Handle MQTT event paradigma/heating/readmemory Payload {event.payload}")
				startaddr = -1
				length = -1
				frequency = -1
				required = ["startaddr", "length"]
				try:
					data = json.loads(event.payload)
					if all(k in data for k in required):
						startaddr = int(data["startaddr"])
						length = int(data["length"])
					else:
						print (data["startaddr"] + " could not be found")

					if "frequency" in data:
						frequency = int(data["frequency"])
						if frequency >= 30:		# smalles possible interval is 30 seconds
							actions.append(LogMessage(f"Setup Memory Watch every {frequency}s on address 0x{startaddr:04X} for {length} bytes"))
							self.event_queue.put_nowait(
								StartMemoryWatchEvent(
									start_address=startaddr,
									length=length,
									frequency_s=frequency
								)
							)
						elif frequency == -1:		# stop watching
							actions.append(LogMessage(f"Cancel Memory Watch on address 0x{startaddr:04X} for {length} bytes"))
							self.event_queue.put_nowait(
								StopMemoryWatchEvent(
									start_address=startaddr,
									length=length
								)
							)
						else:
							actions.append(LogMessage(f"Readmemory ignored due to invalid parameters frequency={frequency}"))
					else:
						mypayload = bytes([startaddr>>8, startaddr&0xff, length&0xff])
						actions.append(LogMessage(f"Sending cmd=0x0A, payload={mypayload}"))
						actions.append(SendSerial(request=CMD_READ_MEMORY, payload=mypayload))

				except json.JSONDecodeError as exc:
					actions.append(LogMessage(f"Failed to decode the payload of {event.topic} : {event.payload} with {exc}"))
					self.log.error(f"Failed to decode the payload of paradigma/heating/readmemory : {event.payload} with {exc}")

			else:
				self.log.debug (f"Handle unknown MQTT event  Payload {event.payload}")
				actions.append(LogMessage(f"Unknown MQTT topic: {event.topic}"))



		elif isinstance(event, SerialFrameReceived):
			try:
				(retval, data) = self.msg_parser.parseMessage(event.cmd, event.payload)
			except ProtocolError as exc:
				actions.append(LogMessage(f"Protocol Error: {exc}"))
				self.log.exception(f"Protocol Error: {exc}")
				return actions
			except Exception as exc:
				actions.append(LogMessage(f"Unexpected Parser Error: {exc}"))
				self.log.exception(f"Unexpected Parser Error: {exc}")
				return actions

			if retval == CONFIRM_START_MONITORING:
				self.awaiting_response = True
				self.dataset1_received = False
				self.dataset2_received = False
#				actions.append(LogMessage("COM: Start Monitoring Command confirmed"))
				self.log.info("COM: Start Monitoring Command confirmed")
			elif retval == CONFIRM_STOP_MONITORING:
#				actions.append(LogMessage("COM: Stop Monitoring Command confirmed"))
				self.log.info("COM: Stop Monitoring Command confirmed")
				self.awaiting_response = False
			elif retval == CONFIRM_START_READ_VERSION:
#				actions.append(LogMessage("COM: Start Read Version Command confirmed"))
				self.log.info("COM: Start Read Version Command confirmed")
				self.awaiting_version_info = True
			elif retval == VERSION_INFO:
				actions.append(LogMessage(f"COM: Version ist {self.msg_parser.parseVersion(data)}"))
				if self.awaiting_version_info:
					self.awaiting_version_info = False
				else:
#					actions.append(LogMessage(f"COM: Recevied repeated  Version info"))
					self.log.info(f"COM: Recevied repeated  Version info")
				actions.append(SendSerial(request=CMD_STOP_READ_VERSION, payload=[]))
			elif retval == CONFIRM_STOP_READ_VERSION:
#				actions.append(LogMessage("COM: Stop Read Version Command confirmed"))
				self.log.info("COM: Stop Read Version Command confirmed")
			elif retval == CONFIRM_WRITE_MEMORY:
#				actions.append(LogMessage("COM: Write memory Command confirmed"))
				self.log.info("COM: Write memory Command confirmed")
			elif retval == DATASET1:
				actions.append(LogMessage("COM: DATASET1 received"))
				elements = self.msg_parser.parseDataset1(data)
				if self.awaiting_response:
					self.dataset1_received = True
				if self.dataset2_received:
					actions.append(SendSerial(request=CMD_STOP_MONITORING, payload=[]))
					self.dataset1_received = False
					self.dataset2_received = False
				for element in elements:
					actions.append(PublishMqtt(topic=element[0], payload=element[1]))
			elif retval == DATASET2:
				actions.append(LogMessage("COM: DATASET2 recevied"))
				elements = self.msg_parser.parseDataset2(data)
				if self.awaiting_response:
					self.dataset2_received = True
				if self.dataset1_received:
					actions.append(SendSerial(request=CMD_STOP_MONITORING, payload=[]))
					self.dataset1_received = False
					self.dataset2_received = False
				for element in elements:
					actions.append(PublishMqtt(topic=element[0], payload=element[1]))
			elif retval == MEMORY:
#				actions.append(LogMessage("COM: Read message response"))
				self.log.info("COM: Read message response")
				address = data[0]
				length = data[1]
				key = (address, length)
#				print (f"Addr = {address:04X}h, Length = {length:02X}h, Number of data byte = {len(data[2])}, Data = {data[2]}")
				# check if a task is running requesting this data
				if key in self.memory_watch_tasks:
					# Post the result in a json message
#					mqtt_payload = ",".join(map(str, data[2]))
					mqtt_payload = ",".join(f"0x{x:02X}" for x in data[2])
					actions.append(PublishMqtt(topic="paradigma/heating/readMemory/cyclic", payload=mqtt_payload))
				else:
					Zeitprogramme = ["Heizzeitprogramm 1 HK1", "Heizzeitprogramm 2 HK1", "Heizzeitprogramm 3 HK1", "Heizzeitprogramm 1 HK2", "Heizzeitprogramm 2 HK2", "Heizzeitprogramm 3 HK2", "Warmwasserzeitprogramm 1", "Warmwasserzeitprogramm 2"]
					elements = self.msg_parser.parseMemory(address, length, data[2])
					for element in elements:
						if element[0] in Zeitprogramme:
							topic = "paradigma/heating/read/" + element[0]
							payload = element[1]
							mqtt_payload = json.dumps(payload, ensure_ascii=False)
							actions.append(PublishMqtt(topic=topic, payload = mqtt_payload))
						else:
							payload = dict(elements)
							mqtt_payload = json.dumps(payload, ensure_ascii=False)
							actions.append(PublishMqtt(topic="paradigma/heating/readMemory", payload = mqtt_payload))

			else:
				actions.append(LogMessage("Received invalid COM Message " + str([f"{d:02X}" for d in event.payload])))
				self.log.error("Received invalid COM Message " + str([f"{d:02X}" for d in event.payload]))
		else:
			actions.append(LogMessage(f"Unhandled event type: {type(event).__name__}"))

		return actions

	async def execute_action(self, action):
		if isinstance(action, SendSerial):
			print ("******* Send action request="+ str([f"{d:02X}" for d in action.request]) + ", payload=" + str([f"{d:02X}" for d in action.payload]))
			await self.serial_tx_queue.put(action)

		elif isinstance(action, PublishMqtt):
			await asyncio.to_thread(
				self.publish_mqtt,
				action.topic,
				action.payload)

		elif isinstance(action, LogMessage):
			print(action.text)

		elif isinstance(action, StartMemoryWatch):
			await self.start_memory_watch(
				start_address=action.start_address,
				length=action.length,
				frequency_s=action.frequency_s
			)
		elif isinstance(action, StopMemoryWatch):
			await self.stop_memory_watch(
				start_address=action.start_address,
				length=action.length
			)

	async def event_loop_task(self):
		await self.execute_action(SendSerial(request=CMD_START_READ_VERSION, payload=[]))
		while self.running:
			event = await self.event_queue.get()
			actions = self.handle_event(event)

			for action in actions:
				await self.execute_action(action)

	async def run(self):
		tasks = [
			asyncio.create_task(self.periodic_query_task()),
			asyncio.create_task(self.serial_reader_task()),
			asyncio.create_task(self.serial_writer_task()),
			asyncio.create_task(self.event_loop_task()),
			]

		try:
			await asyncio.gather(*tasks)
		finally:
			self.running = False
			for t in tasks:
				t.cancel()

