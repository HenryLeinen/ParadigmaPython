#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import serial
import getopt
import os
import time
import logging
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

logging.basicConfig(filename="paradigma.log", level=logging.INFO)

# Set the target MQTT host to whom to post
mqtt_host = "leinihomesrv"

# Set the client ID which identifies us
mqtt_client_id = "LeiniPi1:paradigma.py"

# Pathname for where to store the paradigma data
dir_name = "/dev/paradigma"

# Remember if we are connected to the MQTT broker
mqtt_connected = False

# Make sure the path exists. Create it if necessary
if not os.path.exists(dir_name):
	os.makedirs(dir_name)

mqtt_init = [	{'topic':"homie/Paradigma/$name", 	'payload':"Paradigma", 		'retain':"true"},
		{'topic':"homie/Paradigma/$homie", 	'payload':"3.0", 		'retain':"true"},
		{'topic':"homie/Paradigma/$state", 	'payload':"ready",		'retain':"true"},
		{'topic':"homie/Paradigma/$extensions",	'payload':""},
		{'topic':"homie/Paradigma/$implementation", 'payload':"Raspberry Pi Zero"},
		{'topic':"homie/Paradigma/$nodes", 	'payload':"Fuehler,Warmwasser,Puffer,Heizkreis[],Kessel", 	'retain':"true"},

		{'topic':"homie/Paradigma/Fuehler/$name",	'payload':"Fuehler", 	'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/$properties",	'payload':"Aussentemperatur,Stoercode", 'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/Aussentemperatur/$name", 	'payload':"Aussentemperatur",	'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/Aussentemperatur/$unit",	'payload':"%°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/Aussentemperatur/$datatype",	'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/Aussentemperatur/$format",	'payload':"-40:80",		'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/Aussentemperatur/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/Stoercode/$name",		'payload':"Stoercode",		'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/Stoercode/$datatype",		'payload':"integer",		'retain':"true"},
		{'topic':"homie/Paradigma/Fuehler/Stoercode/$settable",		'payload':"false",		'retain':"true"},

		{'topic':"homie/Paradigma/Warmwasser/$name",	'payload':"Warmwasser Temperatur", 'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/$properties",'payload':"Temperatur,Soll", 'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/Temperatur/$name",		'payload':"Warmwasser Temperatur", 	'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/Temperatur/$unit",		'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/Temperatur/$datatype",	'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/Temperatur/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/Soll/$name",		'payload':"Warmwasser Solltemperatur",	'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/Soll/$unit",		'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/Soll/$settable",		'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Warmwasser/Soll/$datatype",		'payload':"float",		'retain':"true"},

		{'topic':"homie/Paradigma/Puffer/$name",	'payload':"Puffer Temperaturen",	'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/$properties",	'payload':"Oben,Unten,Soll",	'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Oben/$name",			'payload':"Puffertemperatur Oben",	'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Oben/$unit",			'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Oben/$datatype",		'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Oben/$settable",		'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Unten/$name",			'payload':"Puffertemperatur Unten",	'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Unten/$unit",			'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Unten/$datatype",		'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Unten/$settable",		'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Soll/$name",			'payload':"Puffer Solltemperatur",	'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Soll/$unit",			'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Soll/$datatype",		'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Puffer/Soll/$settable",		'payload':"false",		'retain':"true"},

		{'topic':"homie/Paradigma/Kessel/$name",	'payload':"Kessel",			'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/$properties",	'payload':"Vorlauf,Ruecklauf,Zirkulationstemperatur,Betriebsstunden,Starts,Stoercode",	'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Vorlauf/$name",		'payload':"Vorlauftemperatur",	'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Vorlauf/$unit",		'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Vorlauf/$datatype",		'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Vorlauf/$settable",		'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Ruecklauf/$name",		'payload':"Ruecklauftemperatur",	'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Ruecklauf/$unit",		'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Ruecklauf/$datatype",		'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Ruecklauf/$settable",		'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Zirkulationstemperatur/$name",		'payload':"Zirkulationstemperatur",	'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Zirkulationstemperatur/$unit",		'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Zirkulationstemperatur/$datatype",		'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Zirkulationstemperatur/$settable",		'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Betriebsstunden/$name",		'payload':"Betriebsstunden",	'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Betriebsstunden/$unit",		'payload':"h",			'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Betriebsstunden/$datatype",		'payload':"integer",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Betriebsstunden/$settable",		'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Starts/$name",		'payload':"Anzahl Kesselstarts",	'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Starts/$unit",		'payload':" ",			'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Starts/$datatype",		'payload':"integer",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Starts/$settable",		'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Stoercode/$name",		'payload':"Stoercode Kessel",	'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Stoercode/$datatype",		'payload':"integer",		'retain':"true"},
		{'topic':"homie/Paradigma/Kessel/Stoercode/$settable",		'payload':"false",		'retain':"true"},

		{'topic':"homie/Paradigma/Heizkreis/$name",		'payload':"Heizkreise",			'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/$properties",	'payload':"Raumtemperatur,Vorlauftemperatur,Ruecklauftemperatur,Raumsoll,Vorlaufsoll,Ruecklaufsoll,Betriebsart,Leistung", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/$array",		'payload':"1-2",			'retain':"true"},

		{'topic':"homie/Paradigma/Heizkreis/Raumtemperatur/$name",	'payload':"Raumtemperatur", 	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Raumtemperatur/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Raumtemperatur/$unit",	'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Raumtemperatur/$datatype",	'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Vorlauftemperatur/$name",	'payload':"Vorlauf Temperatur", 	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Vorlauftemperatur/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Vorlauftemperatur/$unit",	'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Vorlauftemperatur/$datatype",	'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Ruecklauftemperatur/$name",	'payload':"Ruecklauf Temperatur", 	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Ruecklauftemperatur/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Ruecklauftemperatur/$unit",	'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Ruecklauftemperatur/$datatype",	'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Raumsoll/$name",	'payload':"Solltemperatur Raum", 	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Raumsoll/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Raumsoll/$unit",	'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Raumsoll/$datatype",	'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Vorlaufsoll/$name",	'payload':"Solltemperatur Vorlauf", 	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Vorlaufsoll/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Vorlaufsoll/$unit",	'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Vorlaufsoll/$datatype",	'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Ruecklaufsoll/$name",	'payload':"Solltemperatur Ruecklauf", 	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Ruecklaufsoll/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Ruecklaufsoll/$unit",	'payload':"°C",			'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Ruecklaufsoll/$datatype",	'payload':"float",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Betriebsart/$name",	'payload':"Betriebsart", 	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Betriebsart/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Betriebsart/$datatype",	'payload':"integer",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Leistung/$name",	'payload':"Leistung", 	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Leistung/$settable",	'payload':"false",		'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Leistung/$unit",	'payload':"W",			'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis/Leistung/$datatype",	'payload':"integer",		'retain':"true"},

		{'topic':"homie/Paradigma/Heizkreis_1/Raumtemperatur/$name",	'payload':"Raumtemperatur Heizkreis 1",	'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_1/Vorlauftemperatur/$name",		'payload':"Vorlauftemperatur Heizkreis 1", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_1/Ruecklauftemperatur/$name",		'payload':"Ruecklauftemperatur Heizkreis 1", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_1/Raumsoll/$name",		'payload':"Solltemperatur Raum Heizkreis 1", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_1/Vorlaufsoll/$name",		'payload':"Solltemperatur Vorlauf Heizkreis 1", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_1/Ruecklaufsoll/$name",		'payload':"Solltemperatur Ruecklauf Heizkreis 1", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_1/Betriebsart/$name",		'payload':"Betriebsart Heizkreis 1", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_1/Leistung/$name",			'payload':"Leistung Heizkreis 1", 'retain':"true"},

		{'topic':"homie/Paradigma/Heizkreis_2/Raumtemperatur/$name",	'payload':"Raumtemperatur Heizkreis 2", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_2/Vorlauftemperatur/$name",		'payload':"Vorlauftemperatur Heizkreis 2", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_2/Ruecklauftemperatur/$name",		'payload':"Ruecklauftemperatur Heizkreis 2", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_2/Raumsoll/$name",		'payload':"Solltemperatur Raum Heizkreis 2", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_2/Vorlaufsoll/$name",		'payload':"Solltemperatur Vorlauf Heizkreis 2", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_2/Ruecklaufsoll/$name",		'payload':"Solltemperatur Ruecklauf Heizkreis 2", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_2/Betriebsart/$name",		'payload':"Betriebsart Heizkreis 2", 'retain':"true"},
		{'topic':"homie/Paradigma/Heizkreis_2/Leistung/$name",			'payload':"Leistung Heizkreis 2", 'retain':"true"}

	]


def UnsignedToSignedInt(d) :
	if d > 32768:
		return d - 65536
	else:
		return d

def BcdToDec(c) :
	return (c >> 4)*10 + (c&0x0f)

def writeInFile(fn, d, s) :
	global mqtt_connected
	f = open ("/dev/paradigma/"+fn, "w")
	f.write(str(d))
	f.close()
	if (mqtt_connected):
		client.publish("fhem/Heizung/"+fn, d)
		client.publish("homie/Paradigma/"+s, d)
	else :
		print("mqtt not connected")


class DateTime(object):
	def __init__(self, dt):
		self.Day = BcdToDec(dt[0])
		self.Month = BcdToDec(dt[1])
		self.Hour = BcdToDec(dt[3])
		self.Minute = BcdToDec(dt[2])


class Dataset1(object):
	def __init__(self, dataset):
		self.dataset = dataset
	
	def DateTime(self):
		return DateTime(self.dataset[0:4])

	def Aussentemp(self):
		return UnsignedToSignedInt(self.dataset[5] + self.dataset[4]*256) / 10.0

	def Warmwassertemp(self):
		return (self.dataset[7] + self.dataset[6]*256) / 10.0

	def Kesselvorlauf(self):
		return (self.dataset[9] + self.dataset[8]*256) / 10.0
	
	def Kesselruecklauf(self):
		return (self.dataset[11]+ self.dataset[10]*256) /10.0

	def RaumtemperaturHK1(self):
		return (self.dataset[13]+ self.dataset[12]*256) /10.0

	def RaumtemperaturHK2(self):
		return (self.dataset[15]+ self.dataset[14]*256) /10.0

	def VorlauftemperaturHK1(self):
		return (self.dataset[17]+ self.dataset[16]*256) /10.0

	def VorlauftemperaturHK2(self):
		return (self.dataset[19]+ self.dataset[18]*256) /10.0

	def RuecklauftemperaturHK1(self):
		return (self.dataset[21]+ self.dataset[20]*256) /10.0

	def RuecklauftemperaturHK2(self):
		return (self.dataset[23]+ self.dataset[22]*256) /10.0

	def PuffertemperaturOben(self):
		return (self.dataset[25]+ self.dataset[24]*256) /10.0

	def PuffertemperaturUnten(self):
		return (self.dataset[27]+ self.dataset[26]*256) /10.0

	def Zirkulationstemperatur(self):
		return (self.dataset[29]+ self.dataset[28]*256) /10.0

	def Dump(self):
		writeInFile("Aussen", self.Aussentemp(), "Fuehler/Aussentemperatur")
		writeInFile("Warmwasser", self.Warmwassertemp(), "Warmwasser/Temperatur")
		writeInFile("Kesselvorlauf", self.Kesselvorlauf(), "Kessel/Vorlauf")
		writeInFile("Kesselruecklauf", self.Kesselruecklauf(), "Kessel/Ruecklauf")
		writeInFile("RaumHK1", self.RaumtemperaturHK1(), "Heizkreis_1/Raumtemperatur")
		writeInFile("RaumHK2", self.RaumtemperaturHK2(), "Heizkreis_2/Raumtemperatur")
		writeInFile("VorlaufHK1", self.VorlauftemperaturHK1(), "Heizkreis_1/Vorlauftemperatur")
		writeInFile("VorlaufHK2", self.VorlauftemperaturHK2(), "Heizkreis_2/Vorlauftemperatur")
		writeInFile("RuecklaufHK1", self.RuecklauftemperaturHK1(), "Heizkreis_1/Ruecklauftemperatur")
		writeInFile("RuecklaufHK2", self.RuecklauftemperaturHK2(), "Heizkreis_2/Ruecklauftemperatur")
		writeInFile("PufferOben", self.PuffertemperaturOben(), "Puffer/Oben")
		writeInFile("PufferUnter", self.PuffertemperaturUnten(), "Puffer/Unten")
		writeInFile("Zirkulation", self.Zirkulationstemperatur(), "Kessel/Zirkulationstemperatur")
		return 0

class Dataset2(object) :
	def __init__(self, dataset) :
		self.dataset = dataset

	def RaumsollHK1(self) :
		return (self.dataset[1] + self.dataset[0] * 256) / 10.0

	def RaumsollHK2(self) :
		return (self.dataset[3] + self.dataset[2] * 256) / 10.0

	def VorlaufsollHK1(self) :
		return (self.dataset[5] + self.dataset[4] * 256) / 10.0

	def VorlaufsollHK2(self) :
		return (self.dataset[7] + self.dataset[6] * 256) / 10.0

	def Warmwassersoll(self) :
		return (self.dataset[9] + self.dataset[8] * 256) / 10.0

	def Puffersoll(self) :
		return (self.dataset[11]+ self.dataset[10]* 256) / 10.0

	def Betriebsstunden(self) :
		return (self.dataset[17] + (self.dataset[16]<<8) + (self.dataset[15]<<16) + (self.dataset[14]<<24))

	def AnzahlKesselstarts(self) :
		return (self.dataset[21] + (self.dataset[20]<<8) + (self.dataset[19]<<16) + (self.dataset[18]<<24))

	def StoercodeKessel(self) :
		return UnsignedToSignedInt(self.dataset[23] + (self.dataset[22]<<8))

	def StoercodeFuehler(self) :
		return self.dataset[24]

	def BetriebsartHK1(self) :
		return self.dataset[25]

	def NiveauHK1(self) :
		return self.dataset[26]

	def BetriebsartHK2(self) :
		return self.dataset[27]
	
	def NiveauHK2(self) :
		return self.dataset[28]

	def LeistungPHK1(self) :
		return self.dataset[29]

	def LeistungPHK2(self) :
		return self.dataset[30]

	def LeistungPk(self) :
		return self.dataset[31]

	def Dump(self) :
		writeInFile("RaumsollHK1", self.RaumsollHK1(), "Heizkreis_1/Raumsoll")
		writeInFile("RaumsollHK2", self.RaumsollHK2(), "Heizkreis_2/Raumsoll")
		writeInFile("VorlaufsollHK1", self.VorlaufsollHK1(), "Heizkreis_1/Vorlaufsoll")
		writeInFile("VorlaufsollHK2", self.VorlaufsollHK2(), "Heizkreis_2/Vorlaufsoll")
		writeInFile("Warmassersoll",self.Warmwassersoll(), "Warmwasser/Soll")
		writeInFile("Puffersoll", self.Puffersoll(), "Puffer/Soll")
		writeInFile("BetriebsartHK1", self.BetriebsartHK1(), "Heizkreis_1/Betriebsart")
		writeInFile("LeistungPHK1", self.LeistungPHK1(), "Heizkreis_1/Leistung")
		writeInFile("LeistungPHK2", self.LeistungPHK2(), "Heizkreis_2/Leistung")
		writeInFile("Betriebsstunden", self.Betriebsstunden(), "Kessel/Betriebsstunden")
		writeInFile("AnzahlKesselstarts", self.AnzahlKesselstarts(), "Kessel/Starts")
		writeInFile("Stoercode Kessel", self.StoercodeKessel(), "Kessel/Stoercode")
		writeInFile("Stoercode Fuehler", self.StoercodeFuehler(), "Fuehler/Stoercode")
		return 1 

def _getChecksum(data):
	chk = 0
	for i in data:
		chk = chk + i
	chk = ~chk + 1
	chk = chk & 0xff
	return chk

def _sendRequest(request, response, withData):
	output = ""
	received_char = 0
	received_data = 0
	responseData = []
	print "Sending request"
	ser.write(''.join([chr(i) for i in request]))
	while True:
		output = ser.read(1)
		if len(output) == 0:
			print "Sending request"
			ser.write(''.join([chr(i) for i in request]))
			received_char = 0
			received_data = 0
			responseData = []
		else:
			if received_char < len(response):
				if response[received_char] == ord(output):
					received_char += 1
					if received_char == len(response):
						print "Received response"
						if withData == 0:
							print "done"
							return 1
						else:
							print "Awaiting dats"
				else:
					if response[0] == ord(output):
						received_char = 1
					else :
						received_char = 0
			else:
				if received_data > 1:
					if received_data == responseData[1]+2:
						print "Received checksum" + hex(ord(output))
						if ord(output) == _getChecksum(responseData):
							print "Successfully received data"
							return responseData[1], responseData[2:]
						else:
							print "Received data has checksum error. (Received:%d, calculated:%d" % ( ord(output), _getChecksum(responseData))
							return 0
				responseData += [ord(output)]
				received_data += 1
				if responseData[0] != 0xfd:
					received_data = 0
					responseData = []
					error_cases += 1
					if error_cases > 256:
						print "Unexpected data received. Terminating."
						return 0


def _open():
	ret = _sendRequest([0x0a, 0x01, 0x14, 0xe1], [0x0a, 0x01, 0x14, 0xe1], 0)
	if ret == 1:
		print "Successfully opened !"
	else:
		print "Failed to open"
	return ret

def _close():
	ret = _sendRequest([0x0a, 0x01, 0x17, 0xde], [0x0a, 0x01, 0x17, 0xde], 0)
	if ret == 1:
		print "Successfully closed !"
	else:
		print "Failed to close"
	return ret

	
def _queryController():
	ret, response = _sendRequest([0x0a, 0x01, 0x16, 0xdf], [0x0a, 0x01, 0x16, 0xdf], 1)
	if ret > 0:
		print "Successfully queried controller : Received ", ret, " items:", ''.join([hex(i) for i in response])
	else:
		print "Failed to query controller !"

def _listenData(did):
	_open();
	state = "waiting"
	processing = True
	dataset = []
	checksum = 0
	while processing:
		output = ser.read()
		if len(output) > 0 :
				for o in output :
					if state == "waiting" :
						msg_len = 0
						dataset = []
						dset_id = 0
						if (ord(o) == 0xfc) or (ord(o) == 0xfd) :
							state = "length"
							checksum = ord(o)
							print "Tag ", hex(ord(o)), " received !"
						else :
							print ",", hex(ord(o))
					elif state == "length" :
						msg_len = ord(o)
						checksum += ord(o)
						print ("Length (" + hex(ord(o)) + ") received !")
						state = "message_id"
					elif state == "message_id" :
						if (ord(o) != 0x0c) :
							print ("Incorrect message type " + hex(ord(o)))
							state = "waiting"
						else :
							print ("Correct message type received ")
							checksum += ord(o)
							state = "dataset_id"
					elif state == "dataset_id" :
						dset_id = ord(o)
						if ((dset_id > 0) and (dset_id < 4)):
							recvd_data = 0
							dataset = []
							checksum += ord(o)
							print ("Receiving dataset id " + str(dset_id) + " received !")
							state = "receive_data"
						else:
							print ("Invalid dataset id " + hex(ord(o)))
							state = "waiting"
					elif state == "receive_data" :
						dataset = dataset + [ord(o)]
						checksum += ord(o)
						recvd_data = recvd_data + 1
						if (len(dataset)+2 == msg_len) :
							state = "checksum"
					elif state == "checksum" :
						checksum += ord(o)
						if ((checksum & 0xff) != 0) :
							print ('Checksum error (remainder is ' + hex(checksum&255)+ '), Received checksum is ', hex(ord(o)), ' !')
							state = "waiting"
							processing = False
						else :
							print ("Successfully received data packet from paradigma !")
							if dset_id == 1 :
								d = Dataset1(dataset)
								d.Dump()
								print ('Datum = ' + str(d.DateTime().Day) + "." + str(d.DateTime().Month) + '  ' + str(d.DateTime().Hour) + ':' + str(d.DateTime().Minute))
								print ('Aussentemp = ' + str(d.Aussentemp()))
								print ('Warmwasser = ' + str(d.Warmwassertemp()))
								print ('Kesselvorlauf = ' + str(d.Kesselvorlauf()))
								print ('Kesselruecklauf = ' + str(d.Kesselruecklauf()))
								state = "waiting"
							elif dset_id == 2 :
								d = Dataset2(dataset)
								d.Dump()
								print ('Betriebsstunden = ' + str(d.Betriebsstunden()))
								print ('Anzahl Kesselstarts = ' + str(d.AnzahlKesselstarts()))
								print ('Stoercode Fuehler = ' + str(d.StoercodeFuehler()))
								print ('Stoercode Kessel = ' + str(d.StoercodeKessel()))
								print ('Betriebsart HK1 = ' + str(d.BetriebsartHK1()))
								print ('Warmwassersoll = ' + str(d.Warmwassersoll()))
								print ('Puffersoll = ' + str(d.Puffersoll()))
								state = "waiting"
							else :
								state = "waiting"
							if dset_id == did :
								processing = False
		else :
			print "Timeout"
			processing = False

	return 1
	
# Callback to indicate that connection to MQTT server was successful
def on_connect(client, userdata, flags, rc):
	global mqtt_connected
	logging.debug("mqtt connected")
	print ('Connected with result code : ' + str(rc))
	mqtt_connected = True

def on_disconnect(client, userdata, rc):
	global mqtt_connected
	if rx != 0:
		print ('Unexpected disconnection!')
		logging.debug("Unexpected mqtt disconnect")
	else :
		logging.debug("mqtt disconnected")
		print ('Disconnected !') 
	mqtt_connected = False

def on_message(client, userdata, message):
	print ('Received message ' + str(message.payload) + ' on topic ' + message.topic + ' with QoS ' + str(message.qos))




# Create the MQTT client
client = mqtt.Client(client_id=mqtt_client_id, protocol=mqtt.MQTTv31)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.username_pw_set('pi', 'Quantenoptik1')
client.connect(mqtt_host, 1883, 60)

client.loop_start()

# time.sleep(1)

# Publish the "HOMIE" device describing parts via MQTT
print ('Start HOMIE-Device publishing')
for x in mqtt_init:
	print ('Topic: ' + x['topic'])
	client.publish(topic=x['topic'], payload=x['payload'], retain=True)
print ('Done HOMIE-Device publishing')


opts, extraparams = getopt.getopt(sys.argv[1:], "coql", ["close", "open", "query", "listen"])

if (not os.path.exists('/dev/paradigma')) :
	os.makedirs('/dev/paradigma', 0x777, True)

ser = serial.Serial("/dev/ttyUSB0", timeout=15.0)
print "Serial was opened !"

for o,p in opts :
	if o in ['-o', '--open']:
		print ("Opening")
		_open()
		exit(0)
	if o in ['-c', '--close']:
		print ("Closing")
		_close()
		exit(0)
	if o in ['-q', '--query']:
		print ("Querying")
		_queryController()
		exit(0)
	if o in ['-l', '--listen']:
		print ("Listenening for data packets")
		_listenData(1)
		_listenData(2)
#		exit(0)

client.disconnect()

ser.close()

client.loop_stop()

time.sleep(4)

sys.exit(0)


