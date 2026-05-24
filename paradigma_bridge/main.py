#!/usr/bin/env python3

import logging
import serial
import asyncio

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

	ser = serial.Serial("/dev/ttyUSB0", timeout=0)

	controller = Controller(ser, log)

	asyncio.run(controller.run())

	print("Finishing")

