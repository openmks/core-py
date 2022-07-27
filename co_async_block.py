import threading
import json
import traceback

from core import co_logger

class AsyncBlock():
	def __init__(self, network, ip, port):
		self.Network = network
		self.IP = ip
		self.Port = port

		self.Locker = threading.Lock()
		self.Signal = threading.Event()
		self.PayloadResponse = None
		self.AsyncDataArrived = None

		self.Hash = self.Network.Connect(self.IP, self.Port, self.Callback)
		if self.Hash is not None:
			pass
	
	def Disconnect(self):
		self.Network.Disconnect(self.IP, self.Port)
	
	def Callback(self, sock, sock_info, data):
		packet = json.loads(data)
		if "event" in packet["header"]["command"]:
			if self.AsyncDataArrived is not None:
				self.AsyncDataArrived(packet["payload"])
		else:
			self.PayloadResponse = packet["payload"]
			# self.Network.Disconnect(self.IP, self.Port)
			self.Signal.set()
	
	def Execute(self, request):
		# hash = self.Network.Connect(self.IP, self.Port, self.Callback)
		if self.Hash is not None:
			try:
				self.Locker.acquire()
				self.Signal.clear()
				self.Network.Send(self.IP, self.Port, json.dumps(request))
				self.Signal.wait(None)
				self.Locker.release()
				return self.PayloadResponse
			except Exception as e:
				co_logger.LOGGER.Log("ServerThread Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
				self.Disconnect()
				self.Locker.release()
		
		return None