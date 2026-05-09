
import logging
import serial
from dataclasses import dataclass


log = logging.getLogger(__name__)





class SerialFrameParser:
	START_BYTES = {0x0A, 0xFC, 0xFD}

	def __init__(self, on_frame_callback):
		# Parser state
		self.on_frame_callback = on_frame_callback
		self._listen_state = "WAIT_CMD"
		self._listen_cmd = 0
		self._listen_length = 0
		self._listen_payload = bytearray()
		self._listen_checksum = 0
		self._listen_invalid_chars = 0

	def _reset_listen_state(self):
		self._listen_state = "WAIT_CMD"
		self._listen_cmd = 0
		self._listen_length = 0
		self._listen_payload = bytearray()
		self._listen_checksum = 0

	def feed(self, byte_value: int):
		"""
		Call this method once for every newly received byte.

		Parameters
		----------
		byte_value : int
		Single byte value in range 0..255
		"""

		if not (0 <= byte_value <= 0xFF):
			raise ValueError(f"byte_value must be in range 0..255, got {byte_value}")

		# ------------------------------------------------------------
		# State: WAIT_CMD
		# ------------------------------------------------------------
		if self._listen_state == "WAIT_CMD":
			if byte_value in self.START_BYTES:
				self._listen_cmd = byte_value
				self._listen_checksum = byte_value
				self._listen_payload = bytearray()
				self._listen_state = "WAIT_LEN"
			else:
				self._listen_invalid_chars += 1
			return

		# ------------------------------------------------------------
		# State: WAIT_LEN
		# ------------------------------------------------------------
		if self._listen_state == "WAIT_LEN":
			self._listen_length = byte_value
			self._listen_checksum += byte_value

			if self._listen_length == 0:
				self._listen_state = "WAIT_CHECKSUM"
			else:
				self._listen_state = "WAIT_PAYLOAD"

			return

		# ------------------------------------------------------------
		# State: WAIT_PAYLOAD
		# ------------------------------------------------------------
		if self._listen_state == "WAIT_PAYLOAD":
			self._listen_payload.append(byte_value)
			self._listen_checksum += byte_value

			if len(self._listen_payload) >= self._listen_length:
				self._listen_state = "WAIT_CHECKSUM"
			return

		# ------------------------------------------------------------
		# State: WAIT_CHECKSUM
		# ------------------------------------------------------------
		if self._listen_state == "WAIT_CHECKSUM":
			received_checksum = byte_value
			self._listen_checksum += received_checksum

			cmd = self._listen_cmd
			payload = bytes(self._listen_payload)

			if (self._listen_checksum & 0xFF) == 0:
				if self._listen_invalid_chars > 0:
					log.error(
						"Recorded %d invalid characters during LISTEN",
						self._listen_invalid_chars
					)
					self._listen_invalid_chars = 0

				# Valid message -> put into FIFO
				self.on_frame_callback(cmd, payload)

			else:
				log.debug("Checksum error in LISTEN")

				if self._listen_invalid_chars > 0:
					log.error(
						"Recorded %d invalid characters during LISTEN",
						self._listen_invalid_chars
					)
					self._listen_invalid_chars = 0

			self._reset_listen_state()
			return

		# Safety fallback
		log.error("Unknown parser state: %s. Resetting.", self._listen_state)
		self._reset_listen_state()

