#!/usr/bin/python
import os
import sys
import time
import struct
import json
import queue
import _thread
import threading

import mks.mks_uart_adaptor as mks_uart_adaptor
import mks.mks_protocol as mks_protocol
import mks.mks_abstract_connector as mks_abstract_connector

class Connector (mks_abstract_connector.AbstractConnector):
	def __init__ (self):
		mks_abstract_connector.AbstractConnector.__init__(self)
		self.ClassName 						= "Connector"
		self.NodeType 						= 0
		self.Adapters						= {}
		self.Protocol 						= mks_protocol.Protocol()
		self.UARTInterfaces 				= []
		self.RecievePacketsWorkerRunning	= False
		# Events
		self.AdaptorDisconnectedEvent 		= None
		self.AdaptorAsyncDataEvent 			= None
		# Data arrived queue
		self.QueueLock      	    		= threading.Lock()
		self.Packets      					= queue.Queue()

		_thread.start_new_thread(self.RecievePacketsWorker, ())
	
	def RecievePacketsWorker (self):
		self.RecievePacketsWorkerRunning = True
		while self.RecievePacketsWorkerRunning == True:
			try:
				item = self.Packets.get(block=True,timeout=None)
				if self.AdaptorAsyncDataEvent is not None:
					self.AdaptorAsyncDataEvent(item["path"], item["data"])
			except Exception as e:
				print ("({classname})# [ERROR] (RecievePacketsWorker) {0}".format(str(e), classname=self.ClassName))

	# MIGHT BE DEPRICATED
	def FindUARTDevices(self):
		dev = os.listdir("/dev/")
		return ["/dev/" + item for item in dev if "ttyUSB" in item]
	
	def ListSerialComPorts(self):
		adaptor = mks_uart_adaptor.Adaptor("", 0)
		serial_devices = adaptor.ListSerialComPorts()
		comports = []
		for item in serial_devices:
			comport = item[0]
			is_comport_connected = False
			comport_type = "unknown"
			if comport in self.Adapters:
				is_comport_connected = True
				comport_type = self.Adapters[comport]["type"]
			comports.append({
				"port": comport,
				"is_connected": is_comport_connected,
				"type": comport_type
			})
		
		return comports
	
	def __Connect(self, path, baud):
		adaptor = mks_uart_adaptor.Adaptor(path, baud)
		adaptor.OnSerialAsyncDataCallback 			= self.OnAdapterDataArrived
		adaptor.OnSerialConnectionClosedCallback 	= self.OnAdapterDisconnected
		if adaptor.Connect(3) is True:
			self.Adapters[path] = {
				"adaptor": adaptor,
				"type": "unknown",
				"info": None
			}
			return True
		return False
	
	def GetUUID (self, path):
		if path in self.Adapters:
			tx_packet = self.Protocol.GetDeviceUUIDCommand()
			rx_packet = self.Adaptor[path]["adaptor"].Send(tx_packet)
			if (len(rx_packet) > 3):
				return rx_packet[6:-1] # "-1" is for removing "\n" at the end (no unpack used)
		return None
	
	def GetDeviceType(self, path):
		if path in self.Adapters:
			tx_packet = self.Protocol.GetDeviceTypeCommand()
			rx_packet = self.Adapters[path]["adaptor"].Send(tx_packet)
			if (len(rx_packet) > 3):
				device_type = ''.join([str(chr(elem)) for elem in rx_packet[3:]])
				self.Adapters[path]["type"] = device_type
				return device_type
		return None
	
	def GetDeviceAdditional(self, path):
		if path in self.Adapters:
			tx_packet = self.Protocol.GetDeviceAdditionalCommand()
			rx_packet = self.Adapters[path]["adaptor"].Send(tx_packet)
			if (len(rx_packet) > 3):
				additional_data = rx_packet[3:]
				return additional_data
		return None
	
	def SingleConnect(self, dev_path, baud):
		# Try for 3 times
		for i in range(1):
			if self.__Connect(dev_path, baud) is True:
				return True
		return False
	
	def SingleDisconnect(self, dev_path):
		try:
			self.Adapters[dev_path]["adaptor"].Disconnect()
			del self.Adapters[dev_path]
		except:
			return False
		return True
	
	def Connect(self, device_type):
		self.NodeType = device_type
		adaptor = mks_uart_adaptor.Adaptor("", 0)
		self.UARTInterfaces = adaptor.ListSerialComPorts()
		for serial_device in self.UARTInterfaces:
			comport = serial_device[0]
			# Try for 3 times
			for i in range(3):
				if self.__Connect(comport, 115200) is True:
					print(self.GetDeviceType(comport))
					break
		return self.Adapters
	
	def FindAdaptor(self, path):
		for key in self.Adapters:
			if key == path:
				return key
		return None
	
	# MIGHT BE DEPRICATED
	def UpdateUARTInterfaces(self):
		changes = []
		interfaces = self.FindUARTDevices()
		# Find disconnected adaptors
		for adaptor in self.Adapters:
			if adaptor["path"] not in interfaces:
				# USB must be disconnected
				changes.append({
					"change": "remove",
					"path": adaptor["path"]
				})
		for interface in interfaces:
			adaptor = self.FindAdaptor(interface)
			if adaptor is None:
				if self.__Connect(interface) is True:
					changes.append({
						"change": "append",
						"path": interface
					})

		if len(changes) > 0:
			print ("({classname})# Changes ({0})".format(changes, classname=self.ClassName))
		
		return changes
	
	def OnAdapterDisconnected(self, path):
		pass

	def OnAdapterDataArrived(self, path, data):
		if len(data) > 3:
			self.QueueLock.acquire()			
			self.Packets.put( {
				'path': path,
				'data': data
			})
			self.QueueLock.release()
		else:
			print ("({classname})# (OnAdapterDataArrived) Data length not meet the required ({0})".format(len(data), classname=self.ClassName))
	
	def Disconnect(self):
		self.IsConnected = False
		self.RecievePacketsWorkerRunning = False
		while len(self.Adapters) > 0:
			key = list(self.Adapters.keys())[0]
			self.SingleDisconnect(key)	

	def IsValidDevice(self):
		return self.IsConnected

	def Send(self, path, packet):
		if path in self.Adapters:
			tx_packet = packet
			rx_packet = self.Adapters[path]["adaptor"].Send(tx_packet)
			return rx_packet
		return None
