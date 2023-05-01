#!/usr/bin/python
import os
import sys
import time
import json
import _thread
import threading
import serial
import serial.tools.list_ports

from core import co_logger

class UART:
	def __init__(self, serialPort = '/dev/ttyUSB0', serialBaud = 38400):
		self.SerialAdapter 				= None
		self.Port 						= serialPort
		self.Baud 						= serialBaud
		self.DataLock 					= threading.Lock()
		self.IsRecieverRunning 			= False
		self.DataBytes 					= None
		self.DataBytesLength 			= 0
		self.BytesPerFrame 				= 1
		self.WithTimeout 				= 1
		
		self.DataArrivedCallback		= None
	
	def Connect(self):
		co_logger.LOGGER.Log("[UART] Connect port {port} with boudrate {boud}...".format(port=self.Port, boud=str(self.Baud)), 1)
		try:
			if self.IsRecieverRunning is True:
				return False
			
			self.SerialAdapter = serial.Serial(write_timeout = 1)
			self.SerialAdapter.port		= self.Port
			self.SerialAdapter.baudrate	= self.Baud

			if (self.WithTimeout > 0):
				self.SerialAdapter.timeout = self.WithTimeout
				self.SerialAdapter.open()
			else:
				self.SerialAdapter.open()

			if self.SerialAdapter is not None:
				_thread.start_new_thread(self.RecieveDataThread, ())
				co_logger.LOGGER.Log("[UART] Connected to port {port} with boudrate {boud}.".format(port=self.Port, boud=str(self.Baud)), 1)
				time.sleep(0.5)
			return True
		except:
			co_logger.LOGGER.Log("[UART] <EXCEPTION> Failed to connect with {} at {} baudrate.".format(str(self.Port), str(self.Baud)), 1)
			# print("[UART] <EXCEPTION> Failed to connect with " + str(self.Port) + ' at ' + str(self.Baud) + ' baudrate.')
			return False
	
	def Disconnect(self):
		self.IsRecieverRunning = False
		if self.SerialAdapter is not None:
			self.SerialAdapter.close()
		
		co_logger.LOGGER.Log("[UART] Disconnect from port {port}.".format(port=self.Port), 1)
		return True
	
	def SetBytesPerFrame(self, byteperframe):
		self.BytesPerFrame = byteperframe

	def RecieveDataThread(self):
		self.IsRecieverRunning = True
		while self.IsRecieverRunning is True:
			try:
				self.DataBytes = self.SerialAdapter.read(self.BytesPerFrame)
				if self.DataBytes != "" and len(self.DataBytes) > 0:
					#print(self.DataBytes)
					self.DataBytesLength = len(self.DataBytes)
					
					if self.DataArrivedCallback is not None:
						self.DataArrivedCallback(self.DataBytes, self.DataBytesLength)
			except:
				pass
		print("[UART] Reciever thread closed.")
	
	def Write(self, data):
		# print ("[OUT] " + ":".join("{:02x}".format(ord(c)) for c in str(data)))
		self.SerialAdapter.write(data.encode())
	
	def WriteBytes(self, data):
		self.SerialAdapter.write(data)
	
	def GetComPorts(self):
		return [port for port in serial.tools.list_ports.comports() if port[2] != 'n/a']
