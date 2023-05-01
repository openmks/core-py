import threading
import json
import traceback

from core import co_logger
from core import co_queue

class WaitingBlock():
	def __init__(self, identification):
		__slots__ = ('Signal', 'SignalTimeout', 'Identification', 'Data', 'RawData', 'TimeoutEvent')
		self.Signal			= threading.Event()
		self.SignalTimeout	= 8.0
		self.Identification = identification
		self.Data 			= None
		self.RawData 		= None
		self.TimeoutEvent 	= None

		self.Signal.clear()
	
	def Wait(self):
		#co_logger.LOGGER.Log("WaitingBlock (Wait) {}".format(self.Identification), 1)
		status = self.Signal.wait(self.SignalTimeout)
		if status is False:
			#co_logger.LOGGER.Log("WaitingBlock (Wait) OUT {} {} {} {}".format(self.Identification, status, self.Signal.is_set(), None), 1)
			if self.TimeoutEvent is not None:
				self.TimeoutEvent(self.Identification)
		else:
			pass
			#co_logger.LOGGER.Log("WaitingBlock (Wait) OUT {} {} {} {}".format(self.Identification, status, self.Signal.is_set(), len(self.RawData)), 1)
		
		return status

	def Release(self):
		#if self.RawData is not None:
		#	co_logger.LOGGER.Log("WaitingBlock (Release) {} {} {}".format(self.Identification, self.Signal.is_set(), len(self.RawData)), 1)
		#else:
		#	co_logger.LOGGER.Log("WaitingBlock (Release) {} {} {}".format(self.Identification, self.Signal.is_set(), None), 1)
		self.Signal.set()
	
	def Clear(self):
		self.Signal.clear()

class AsyncBlock():
	def __init__(self, network, ip, port):
		__slots__ = ('Network', 'IP', 'Port', 'AsyncDataArrived', 'CallbackQueue', 'WaitingBlocks')
		self.Network 			= network
		self.IP 				= ip
		self.Port 				= port
		self.AsyncDataArrived 	= None

		self.CallbackQueue		= co_queue.Manager(self.CallbackQueueHandler)
		self.CallbackQueue.Start()

		# self.RequestCommand 	= ""
		self.WaitingBlocks 		= {}

	def Connect(self):
		self.Hash = self.Network.Connect(self.IP, self.Port, self.Callback)
		if self.Hash is not None:
			pass
	
	def Disconnect(self):
		self.Network.Disconnect(self.IP, self.Port)
	
	def CallbackQueueHandler(self, item):
		try:
			data 		= item["data"]
			sock 		= item["sock"]
			sock_info 	= item["sock_info"]

			#co_logger.LOGGER.Log("AsyncBlock (Callback) {}".format(len(data)), 1)

			packet = json.loads(data)
			command = packet["header"]["command"]
			if "event" in command:
				if self.AsyncDataArrived is not None:
					self.AsyncDataArrived(packet["payload"])
			else:
				if command in self.WaitingBlocks:
					#co_logger.LOGGER.Log("AsyncBlock (Callback) User {}".format(command), 1)
					self.WaitingBlocks[command].Data = packet["payload"]
					self.WaitingBlocks[command].RawData = data
					self.WaitingBlocks[command].Release()
				else:
					#co_logger.LOGGER.Log("AsyncBlock (Callback) Server {}".format(command), 1)
					if self.Network.ServerSockDataArrivedCallback is not None:
						self.Network.ServerSockDataArrivedCallback(sock, sock_info, data)
		except Exception as e:
			co_logger.LOGGER.Log("AsyncBlock (Callback) Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
	
	def Callback(self, sock, sock_info, data):
		self.CallbackQueue.QueueItem({
			"sock": sock,
			"sock_info": sock_info,
			"data": data
		})

	def Execute(self, request):
		waiting_block = None
		if self.Hash is not None:
			try:
				waiting_block = WaitingBlock(request["header"]["command"])
				self.WaitingBlocks[request["header"]["command"]] = waiting_block

				#co_logger.LOGGER.Log("Execute {}".format(request["header"]["command"]), 1)
				self.Network.Send(self.IP, self.Port, json.dumps(request))
				# Note, user should wait on waiting block (might be race condition between send and till Wait function)
			except Exception as e:
				co_logger.LOGGER.Log("AsyncBlock (Execute) Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
		
		return waiting_block

	'''
	def CallbackQueueHandler(self, item):
		try:
			data = item["data"]
			sock = item["sock"]
			sock_info = item["sock_info"]

			# co_logger.LOGGER.Log("AsyncBlock (Callback) {}".format(len(data)), 1)

			packet = json.loads(data)
			if "event" in packet["header"]["command"]:
				if self.AsyncDataArrived is not None:
					self.AsyncDataArrived(packet["payload"])
			else:
				if self.Executing is False:
					if self.Network.ServerSockDataArrivedCallback is not None:
						self.Network.ServerSockDataArrivedCallback(sock, sock_info, data)
						return
				if packet["header"]["command"] == self.RequestCommand:
					co_logger.LOGGER.Log("AsyncBlock (Callback) {}".format(packet["header"]["command"]), 1)
					self.PayloadResponse = packet["payload"]
					self.Signal.set()
		except Exception as e:
			co_logger.LOGGER.Log("AsyncBlock (Callback) Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
	
	def Callback(self, sock, sock_info, data):
		self.CallbackQueue.QueueItem({
			"sock": sock,
			"sock_info": sock_info,
			"data": data
		})

	def Execute(self, request):
		if self.Hash is not None:
			try:
				self.Executing = True
				self.Signal.clear()
				co_logger.LOGGER.Log("Execute IN {}".format(request["header"]["command"]), 1)
				self.RequestCommand = request["header"]["command"]
				self.Network.Send(self.IP, self.Port, json.dumps(request))
				status = self.Signal.wait(self.SignalTimeout)
				self.Executing = False
				if status is True:
					co_logger.LOGGER.Log("Execute OUT {}".format(self.PayloadResponse), 1)
					return self.PayloadResponse
				else:
					co_logger.LOGGER.Log("Execute OUT TIMEOUT {}".format({}), 1)
					return {}
			except Exception as e:
				co_logger.LOGGER.Log("AsyncBlock (Execute) Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
				self.SignalTimeout = 8.0
		
		return None
		'''