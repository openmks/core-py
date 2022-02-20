#!/usr/bin/python
import struct

class Protocol ():
	def GetDeviceUUIDCommand (self):
		return struct.pack("BBBBBB", 0xDE, 0xAD, 0x1, 51, 0xAD, 0xDE)

	def GetDeviceTypeCommand (self):
		return struct.pack("BBBBBB", 0xDE, 0xAD, 0x1, 50, 0xAD, 0xDE)
	
	def GetDeviceAdditionalCommand (self):
		return struct.pack("BBBBBB", 0xDE, 0xAD, 0x1, 52, 0xAD, 0xDE)
	
	#
	# UNDER CONSTRUCTION
	#

	def SetConfigurationRegisterCommand (self):
		return struct.pack("BBBBBB", 0xDE, 0xAD, 0x1, 0x2, 0x1, 0xF)

	def GetConfigurationRegisterCommand (self):
		return struct.pack("BBBB", 0xDE, 0xAD, 0x1, 0x1)

	def SetBasicSensorValueCommand (self, id, value):
		return struct.pack("BBBBBBH", 0xDE, 0xAD, 0x1, 101, 0x3, id, value)

	def SetArduinoNanoUSBSensorValueCommand (self, id, value):
		return struct.pack("BBBBBBH", 0xDE, 0xAD, 0x1, 101, 0x3, int(id), int(value))

	def GetArduinoNanoUSBSensorValueCommand (self, id):
		return struct.pack("BBBBBBH", 0xDE, 0xAD, 0x1, 100, 0x3, int(id), 0x0)

	def GetDeviceInfoCommand (self):
		return struct.pack("BBBB", 0xDE, 0xAD, 0x1, 107)

	def GetDeviceInfoSensorsCommand (self):
		return struct.pack("BBBB", 0xDE, 0xAD, 0x1, 108)

	def SetWindowMessageCommand (self, window_id, msg, value_type, sign, block_type):
		s = bytes(msg)
		return struct.pack("BBBBBBBcc%ds" % (len(s),), 0xDE, 0xAD, 0x1, 103, 0x4 + len(s), window_id, block_type, value_type, sign, s)
	
	#
	# UNDER CONSTRUCTION
	#
