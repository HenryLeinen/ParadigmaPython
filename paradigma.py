#!/usr/bin/python

import sys
import serial
import getopt
import os

def BcdToDec(c) :
	return (c >> 4)*10 + (c&0x0f)

def writeInFile(fn, d) :
	f = open ("/dev/paradigma/"+fn, "w")
	f.write(str(d))
	f.close()

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
		return (self.dataset[5] + self.dataset[4]*256) / 10.0

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
		writeInFile("Aussen", self.Aussentemp())
		writeInFile("Warmwasser", self.Warmwassertemp())
		writeInFile("Kesselvorlauf", self.Kesselvorlauf())
		writeInFile("Kesselruecklauf", self.Kesselruecklauf())
		writeInFile("RaumHK1", self.RaumtemperaturHK1())
		writeInFile("RaumHK2", self.RaumtemperaturHK2())
		writeInFile("VorlaufHK1", self.VorlauftemperaturHK1())
		writeInFile("VorlaufHK2", self.VorlauftemperaturHK2())
		writeInFile("RuecklaufHK1", self.RuecklauftemperaturHK1())
		writeInFile("RuecklaufHK2", self.RuecklauftemperaturHK2())
		writeInFile("PufferOben", self.PuffertemperaturOben())
		writeInFile("PufferUnter", self.PuffertemperaturUnten())
		writeInFile("Zirkulation", self.Zirkulationstemperatur())
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
		return (self.dataset[23] + (self.dataset[22]<<8))

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
		writeInFile("RaumsollHK1", self.RaumsollHK1())
		writeInFile("RaumsollHK2", self.RaumsollHK2())
		writeInFile("VorlaufsollHK1", self.VorlaufsollHK1())
		writeInFile("VorlaufsollHK2", self.VorlaufsollHK2())
		writeInFile("Warmassersoll",self.Warmwassersoll())
		writeInFile("Puffersoll", self.Puffersoll())
		writeInFile("BetriebsartHK1", self.BetriebsartHK1())
		writeInFile("LeistungPHK1", self.LeistungPHK1())
		writeInFile("LeistungPHK2", self.LeistungPHK2())
		writeInFile("Betriebsstunden", self.Betriebsstunden())
		writeInFile("AnzahlKesselstarts", self.AnzahlKesselstarts())
		writeInFile("Stoercode Kessel", self.StoercodeKessel())
		writeInFile("Stoercode Fuehler", self.StoercodeFuehler())
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
	

			

opts, extraparams = getopt.getopt(sys.argv[1:], "coql", ["close", "open", "query", "listen"])

if (not os.path.exists('/dev/paradigma')) :
	os.makedirs('/dev/paradigma', 0x777, True)

ser = serial.Serial("/dev/ttyUSB0", timeout=15.0)
	
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
		exit(0)

serial.Close(ser)

sys.exit(0)


