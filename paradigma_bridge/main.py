#!/usr/bin/env python3

import logging
import serial
import asyncio
import paho.mqtt.client as mqtt

from paradigma_bridge.Controller import  Controller


log 		= logging.getLogger(__name__)
handler 	= logging.FileHandler("/var/log/paradigma.log")
formatter	= logging.Formatter(
			"%(asctime)s (%(levelname)s) %(threadName)s    :  %(message)s"
#			"%(asctime)s %(message)s"
			)

handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.DEBUG)

if __name__ == "__main__":

	def _onConnect(client, userdata, message, rc, properties):
		print("sucessfully connected to MQTT broker")
	def _onMessage(client, userdata, message):
		try:
			payload = message.payload.decode("utf-8").strip()
		except UnicodeDecodeError:
			log.error("Invalid MQTT payload encoding on topic %s", message.topic)
			return

		controller.on_mqtt_message(topic=message.topic, payload=payload)


	ser = serial.Serial("/dev/ttyUSB0", timeout=0)
	client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
	client.connect("leinihomesrv.local", 1883, 60)
	client.user_data_set([])
	client.loop_start()
	client.on_message = _onMessage
	client.on_connect = _onConnect

	client.subscribe("paradigma/heating/#")


	controller = Controller(ser, client, log)

	asyncio.run(controller.run())

	print("Finishing")

