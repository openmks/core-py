import threading
import json
import traceback

from core import co_logger

class AsyncBlock():
	def __init__(self, network, ip, port):
		self.Network = network
		self.IP = ip
		self.Port = port

		self.Signal = threading.Event()
		self.PayloadResponse = None
		self.AsyncDataArrived = None

		self.Hash = self.Network.Connect(self.IP, self.Port, self.Callback)
		if self.Hash is not None:
			pass
	
	def Disconnect(self):
		self.Network.Disconnect(self.IP, self.Port)
	
	def Callback(self, sock, sock_info, data):
		try:
			packet = json.loads(data)
			if "event" in packet["header"]["command"]:
				if self.AsyncDataArrived is not None:
					self.AsyncDataArrived(packet["payload"])
			else:
				self.PayloadResponse = packet["payload"]
				self.Signal.set()
		except Exception as e:
			co_logger.LOGGER.Log("AsyncBlock (Callback) Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
	
	def Execute(self, request):
		if self.Hash is not None:
			try:
				self.Signal.clear()
				self.Network.Send(self.IP, self.Port, json.dumps(request))
				# co_logger.LOGGER.Log("AsyncBlock (Execute) Wait", 1)
				self.Signal.wait(8.0)
				# co_logger.LOGGER.Log("AsyncBlock (Execute) Set", 1)
				return self.PayloadResponse
			except Exception as e:
				co_logger.LOGGER.Log("AsyncBlock (Execute) Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
		
		return None