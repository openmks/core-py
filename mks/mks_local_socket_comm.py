import json
import traceback
import time

from core import co_logger

class MKSSocket():
	def __init__(self, network, handlers):
		self.Network 	= network
		self.Socket 	= None
		self.WSHandlers	= handlers

	def MKSDataArrivedHandler(self, sock, sock_info, data):
		try:
			packet = json.loads(data)
			co_logger.LOGGER.Log("MKSDataArrivedHandler {} {} {}".format(sock, sock_info, packet), 1)
			command = packet["header"]["command"]
			if self.WSHandlers is not None:
				if command in self.WSHandlers.keys():
					message = self.WSHandlers[command](sock, packet)
					if message == "" or message is None:
						return
					packet["payload"] = message
					sock.send(json.dumps(packet).encode())
		except Exception as e:
			co_logger.LOGGER.Log("MKSDataArrivedHandler ({}) Exception: {} \n=======\nTrace: {}=======".format(command, str(e), traceback.format_exc()), 1)
	
	def Run(self):
		self.Network.SetServerSockDataArrivedCallback(self.MKSDataArrivedHandler)
	
	def AsyncSend(self, event_name, data):
		request = {
			"header": {
				"command": "event",
				"timestamp": time.time(),
				"identifier": 0
			},
			"payload": {
				"event": event_name,
				"data": data
			}
		}
		
		for sock in self.Network.Hive.SockMap:
			sock_info = self.Network.Hive.SockMap[sock]
			if sock != self.Network.Hive.ServerSocket:
				sock.send(json.dumps(request).encode())