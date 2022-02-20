#!/usr/bin/python
import os
import sys
import time
import json
import _thread
import threading
import serial
import serial.tools.list_ports

class UART:
	def __init__(self, serialPort = '/dev/ttyUSB0', serialBaud = 38400):
		self.SerialAdapter 				= None
		self.Port 						= serialPort
		self.Baud 						= serialBaud
		self.DataLock 					= threading.Lock()
		self.IsRecieverRunning 			= True
		self.DataBytes 					= None
		self.DataBytesLength 			= 0
		self.BytesPerFrame 				= 1
		self.WithTimeout 				= 1
		
		self.DataArrivedCallback		= None
	
	def Connect(self):
		print ("UART on port {port} with boudrate {boud} CONNECTING  ...".format(port=self.Port, boud=str(self.Baud)))
		try:
			self.SerialAdapter = serial.Serial()
			self.SerialAdapter.port		= self.Port
			self.SerialAdapter.baudrate	= self.Baud

			if (self.WithTimeout > 0):
				self.SerialAdapter.timeout = self.WithTimeout
				self.SerialAdapter.open()
			else:
				self.SerialAdapter.open()

			if self.SerialAdapter is not None:
				_thread.start_new_thread(self.RecieveDataThread, ())
				print ("UART on port {port} with boudrate {boud} CONNECTED ...".format(port=self.Port, boud=str(self.Baud)))
			return True
		except:
			print("Failed to connect with " + str(self.Port) + ' at ' + str(self.Baud) + ' baudrate.')
			return False
	
	def Disconnect(self):
		self.IsRecieverRunning = False
		self.SerialAdapter.close()
		print ("UART on port {port} DISCONNECTED ...".format(port=self.Port))
	
	def SetBytesPerFrame(self, byteperframe):
		self.BytesPerFrame = byteperframe

	def RecieveDataThread(self):
		while self.IsRecieverRunning is True:
			try:
				self.DataBytes = self.SerialAdapter.read(self.BytesPerFrame)
				if self.DataBytes != "" and len(self.DataBytes) > 0:
					#print(self.DataBytes)
					self.DataBytesLength 	= len(self.DataBytes)
					
					if self.DataArrivedCallback is not None:
						self.DataArrivedCallback(self.DataBytes, self.DataBytesLength)
			except:
				pass
		print("UART reciever thread closed ...\n")
	
	def Write(self, data):
		#print ("[OUT] " + ":".join("{:02x}".format(ord(c)) for c in str(data)))
		self.SerialAdapter.write(data.encode())
