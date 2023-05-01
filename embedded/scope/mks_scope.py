import os
import datetime
import queue
import struct
import math
import _thread
import traceback

from core import co_logger
from core import co_file

class Recorder():
	def __init__(self, comport):
		self.ComPort 			= comport
		self.IsRecording		= True
		self.Orders				= queue.Queue()

		self.RawRecordingStatus	= False
		self.RecordingStatus	= False
		self.TakeSnapshotStatus	= False

		self.RawRecordingPath	= ""
		self.RecordingPath		= ""
		self.SnapshotPath		= ""

		self.Stream 			= co_file.File()
		self.DataItems 			= []

		# Create recording folder
		if not os.path.exists("output"):
			os.mkdir("output")

		_thread.start_new_thread(self.RecorderThread, ())
	
	def TakeSnapshot(self):
		self.TakeSnapshotStatus = True
		today = datetime.datetime.today()
		date = today.strftime("%a_%b_%d_%H_%M_%S_%Y")
		file_name = "{}_snapshot_record_{}.csv".format(self.ComPort, date)
		self.SnapshotPath = os.path.join(".","output", file_name)
		self.Stream.Append(self.SnapshotPath, "timestamp, i2v, imon\n")
	
	def SetRawRecording(self, status):
		self.RawRecordingStatus = status
		if self.RawRecordingStatus is True:
			today = datetime.datetime.today()
			date = today.strftime("%a_%b_%d_%H_%M_%S_%Y")
			file_name = "{}_raw_record_{}.csv".format(self.ComPort, date)
			self.RawRecordingPath = os.path.join(".","output", file_name)
			self.Stream.Append(self.RawRecordingPath, "timestamp, i2v, imon\n")
	
	def SetRecording(self, status):
		self.RecordingStatus = status
		if self.RecordingStatus is True:
			today = datetime.datetime.today()
			date = today.strftime("%a_%b_%d_%H_%M_%S_%Y")
			file_name = "{}_record_{}.csv".format(self.ComPort, date)
			self.RecordingPath = os.path.join(".","output", file_name)
			self.Stream.Append(self.RecordingPath, "index,")
			self.Stream.Append(self.RecordingPath, ','.join(self.DataItems)+"\n")	
	
	def AppendRecordOrder(self, data):
		if self.RawRecordingStatus is True or self.RecordingStatus is True or self.TakeSnapshotStatus is True:
			self.Orders.put(data)
	
	def RecorderThread(self):
		# Store to file
		while self.IsRecording is True:
			task = self.Orders.get(block=True,timeout=None)
			try:
				timestamp = task["header"]["ts"]
				delta_ts = task["header"]["delta_ts"]
				# print(task["header"]["index"], timestamp, task["header"]["delta_ts"], len(task["channels"]))
				channel_map = {
					"stream": [],
					"data": 0
				}

				for key in task["channels"]:
					channel = task["channels"][key]
					if channel["type"] > 0 and channel["type"] < 11:
						channel_map["stream"].append(key)
					elif channel["type"] == 20:
						channel_map["data"] = key
				
				if self.TakeSnapshotStatus is True:
					data_to_file = ""
					# Record stream channels
					if len(channel_map["stream"]) > 0:
						stream_size = int(task["channels"][channel_map["stream"][0]]["size"] / 2)
						for index in range(stream_size):
							data_to_file += str(timestamp)
							for i in range(len(channel_map["stream"])):
								stream_id = channel_map["stream"][i]
								data_to_file += "," + str(task["channels"][stream_id]["data"]["y"][index])
							data_to_file += "\n"
							timestamp += delta_ts
						# Append data to csv file
						self.Stream.Append(self.SnapshotPath, data_to_file)
					self.TakeSnapshotStatus = False
				
				if self.RawRecordingStatus is True:
					data_to_file = ""
					# Record stream channels
					if len(channel_map["stream"]) > 0:
						stream_size = int(task["channels"][channel_map["stream"][0]]["size"] / 2)
						for index in range(stream_size):
							data_to_file += str(timestamp)
							for i in range(len(channel_map["stream"])):
								stream_id = channel_map["stream"][i]
								data_to_file += "," + str(task["channels"][stream_id]["data"]["y"][index])
							data_to_file += "\n"
							timestamp += delta_ts
						# Append data to csv file
						self.Stream.Append(self.RawRecordingPath, data_to_file)
				
				if self.RecordingStatus is True:
					if "data" in channel_map:
						data_to_file = ""
						channel_data = task["channels"][channel_map["data"]]["data"]
						data_to_file += str(task["header"]["packet_index"])
						for item in self.DataItems:
							for io in channel_data:
								if io["name"] == item:
									data_to_file += "," + str(io["value"])
									break
						data_to_file += "\n"
						# Append data to csv file
						self.Stream.Append(self.RecordingPath, data_to_file)

			except Exception as e:
				co_logger.LOGGER.Log("AnalyzerThread <EXEPTION>: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
	
class ScopeData():
	def __init__(self):
		__slots__ = ('Structure', 'ChannelId')
		self.ChannelId	= 0
		self.Structure	= []
		
	def CalculateDataSizeForUnpack(self):
		sum = 0
		items_count = 0
		data_types = {
			"s": 0,
			"d": 8,
			"f": 4,
			"q": 8,
			"I": 4,
			"i": 4,
			"H": 2,
			"h": 2,
			"B": 1,
			"b": 1,
			"c": 1
		}

		for item in self.Structure:
			if item["type"] not in data_types:
				type_d = item["type"][-1:]
				count = item["type"][:-1]
				if type_d in data_types:
					sum += int(count)
					items_count += 1
			else:
				sum += data_types[item["type"]]
				items_count += 1

		return sum, items_count
	
	def GenrateDataTypeForUnpack(self):
		structure = "<"
		for item in self.Structure:
			structure += item["type"]

		return structure

	def Parse(self, channel_id, buffer):
		if channel_id == self.ChannelId:
			expected_size, items_count = self.CalculateDataSizeForUnpack()
			if len(buffer) == expected_size:
				structure = self.GenrateDataTypeForUnpack()
				unpacked_data = struct.unpack(structure, buffer)
				data = []
				if len(unpacked_data) == items_count:
					for idx, value in enumerate(unpacked_data):
						error = ""
						try:
							if type(value) is bytes:
								stream = struct.unpack("%dH" % (len(value) / 2), value)
								data.append({
									"name": self.Structure[idx]["name"],
									"value": stream,
									"error": error
								})
							else:
								if (math.isinf(value)):
									value = 0.0
									error += "inf,"
								if (math.isnan(value)):
									value = 0.0
									error += "nan,"
								
								data.append({
									"name": self.Structure[idx]["name"],
									"value": value,
									"error": error
								})
						except Exception as e:
							print(str(e))
							#print("Parse: type of value {} not supported".format(type(value)))						
				else:
					print("Parse: Size of unpacked ({}) different from structured ({})".format(len(unpacked_data), items_count))
				
				return data
			else:
				print("Parse: Size of buffer ({0}) different from expected ({1})".format(len(buffer), expected_size))
		else:
			print("Parse: Channel ({0}) different from expected ({1})".format(channel_id, self.ChannelId))
	
		return None

class Scope():
	def __init__(self, name):
		__slots__ = ('Name', 'Stream', 'AnalyzerWork', 'LocalQueue', 'ScopeChannels', 'DataIsReadyEvent', 'MaxBufferSize', 'CurrentTS', 'PreviouseTS', 'SampleTime', 'Recorder')
		self.Name 					= name
		self.Stream 				= bytes()
		self.AnalyzerWork 			= True
		self.LocalQueue		    	= queue.Queue()
		self.ScopeChannels			= {}
		self.DataIsReadyEvent		= None
		self.DataChannels 			= {}
		self.MaxBufferSize  		= 2048
		# Timestamp
		self.CurrentTS 				= 0
		self.PreviouseTS 			= 0
		self.SampleTime 			= 0
		# Recording
		self.Recorder 				= Recorder(self.Name)
	
	def CalculateDSPSamplingRate(self):
		self.CurrentTS = self.PacketHeader[3]
		if self.PreviouseTS == 0:
			self.PreviouseTS = self.CurrentTS
		else:		
			tsDiff  = self.CurrentTS - self.PreviouseTS
			self.SampleTime = float(tsDiff) / float(self.MaxBufferSize)
			self.PreviouseTS = self.CurrentTS
		
		return float(1 / self.SampleTime)
	
	def AppendChannel(self, id, size, name, type):
		self.ScopeChannels[id] = {
			'data': None,
			'size': size,
			'name': name,
			'type': type
		}
	
	def BindDataChanel(self, channelid, obj):
		self.DataChannels[channelid] = obj
	
	def UpdateStream(self, data):
		self.Stream += data
		working = True
		while working is True:
			index_dead = self.Stream.find(b'\x44\x45\x41\x44') # DEAD
			index_beaf = self.Stream.find(b'\x42\x45\x41\x46') # BEAF
			# print(index_dead, index_beaf, len(self.Stream))
			if index_dead != -1 and index_beaf != -1:
				if index_dead > index_beaf:
					self.Stream = self.Stream[index_beaf+4:len(self.Stream)]
				else:
					package = self.Stream[index_dead:index_beaf+4]
					self.LocalQueue.put(package)
					self.Stream = self.Stream[index_beaf+4:len(self.Stream)]
			else:
				working = False
	
	def AnalyzerThread(self):
		while self.AnalyzerWork is True:
			try:
				buffer = self.LocalQueue.get(block=True,timeout=None)
				self.PacketHeader = struct.unpack('<IHBIB', buffer[:12])
				# print("Packet Header", self.PacketHeader[2], self.PacketHeader[3])

				#	typedef struct {
				#		uint32_t 	magic; // 1145128260
				#		uint16_t 	size;
				#		uint8_t  	index;
				#		uint32_t 	timestamp;
				#		uint8_t		channels_count;
				#		uint8_t		reserved[4];
				#	} PackageHeader;

				# Check if size of packet equal to the size in the header
				if (len(buffer) == int(self.PacketHeader[1])):
					channel_offset = 16
					# Lets go over the channels
					for idx in range(int(self.PacketHeader[4])):
						channel_header = buffer[channel_offset:channel_offset+16]
						channel_header_data = struct.unpack('<BHB', channel_header[:4])
						# print("Channel Header", channel_header_data)

						#	typedef struct {
						#		uint8_t 	id;
						#		uint16_t	bufer_size;
						#		uint8_t		type;
						#		uint8_t		reserved[12];
						#	} ChannelHeader;

						channel_id   = channel_header_data[0]
						channel_size = channel_header_data[1]
						channel_type = channel_header_data[2]
						# print("Channel Header", channel_id, channel_size, channel_type)

						buf_start = channel_offset + 16
						buf_end = buf_start + channel_size

						if channel_id in self.ScopeChannels:
							data_channel = buffer[buf_start:buf_end]
							if channel_type == 1:
								# Byte, Unsigned Char, uint8_t
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('B'*int(self.ScopeChannels[channel_id]["size"]), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"])):
										x_axis.append(idx)
									
									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							if channel_type == 2:
								# Char
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('b'*int(self.ScopeChannels[channel_id]["size"]), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"])):
										x_axis.append(idx)
									
									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 3:
								# Unsigned Short, uint16_t
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('H'*int(self.ScopeChannels[channel_id]["size"] / 2), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"] / 2)):
										x_axis.append(idx)

									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 4:
								# Short
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('h'*int(self.ScopeChannels[channel_id]["size"] / 2), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"] / 2)):
										x_axis.append(idx)

									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 5:
								# Unsigned Int, Unsigned Long, uint32_t
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('I'*int(self.ScopeChannels[channel_id]["size"] / 4), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"] / 4)):
										x_axis.append(idx)
									
									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 6:
								# Int, Long
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('i'*int(self.ScopeChannels[channel_id]["size"] / 4), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"] / 4)):
										x_axis.append(idx)
									
									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 7:
								# Unsigned Long Long, uint64_t
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('Q'*int(self.ScopeChannels[channel_id]["size"] / 8), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"] / 8)):
										x_axis.append(idx)
									
									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 8:
								# Long Long
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('q'*int(self.ScopeChannels[channel_id]["size"] / 8), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"] / 8)):
										x_axis.append(idx)
									
									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 9:
								# Float
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('f' * int(self.ScopeChannels[channel_id]["size"] / 4), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"] / 4)):
										x_axis.append(idx)

									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 10:
								# Double
								if len(data_channel) == int(self.ScopeChannels[channel_id]["size"]):
									y_axis = [x for x in struct.unpack('d' * int(self.ScopeChannels[channel_id]["size"] / 4), data_channel)]
									x_axis = []
									for idx in range(int(self.ScopeChannels[channel_id]["size"] / 4)):
										x_axis.append(idx)

									self.ScopeChannels[channel_id]["data"] = {
										"y": y_axis,
										"x": x_axis
									}
								else:
									pass
							elif channel_type == 20:
								self.ScopeChannels[channel_id]["data"] = self.DataChannels[channel_id].Parse(channel_id, data_channel)
							else:
								pass
						else:
							pass
						channel_offset = channel_offset + 16 + channel_size
					
					self.CalculateDSPSamplingRate()
					data = {
						"header": {
							"index": self.PacketHeader[2],
							"ts": self.PacketHeader[3],
							"delta_ts": self.SampleTime,
							"packet_index": self.PacketHeader[2]
						},
						"channels": self.ScopeChannels
					}

					if self.DataIsReadyEvent is not None:
						self.DataIsReadyEvent(data)
					self.Recorder.AppendRecordOrder(data)
				else:
					# Packet does not met the size validity
					print("AnalyzerThread: Size of buffer ({0}) different from expected ({1})".format(len(buffer), int(self.PacketHeader[1])))

			except Exception as e:
				print("AnalyzerThread", str(e))
				co_logger.LOGGER.Log("AnalyzerThread <EXEPTION>: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
	
	def SetRecordingItems(self, items):
		self.Recorder.DataItems = items

	def Start(self):
		self.AnalyzerWork = True
		_thread.start_new_thread(self.AnalyzerThread, ())
	
	def Stop(self):
		self.AnalyzerWork = False