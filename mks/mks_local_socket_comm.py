import json
import traceback
import time

from core import co_logger

import threading

class MKSSocket():
	def __init__(self, network, handlers):
		self.Network 	= network
		self.Socket 	= None
		self.WSHandlers	= handlers
		self.Locker 	= threading.Lock()

	def MKSDataArrivedHandler(self, sock, sock_info, data):
		try:
			packet = json.loads(data)
			'''
			{
				'socket': <socket.socket fd=1000, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('192.168.101.10', 10082), raddr=('192.168.101.2', 52577)>, 
				'ip': '192.168.101.2', 
				'port': 52577, 
				'hash': 'f0b4a5c41db50a0091894478b1347d3e', 
				'stream': b'', 
				'timestamp': {
					'created': 1659274750.785868, 
					'last_updated': 1659274757.1712267}
				}
			'''
			co_logger.LOGGER.Log("MKSDataArrivedHandler {} {} {}".format(sock, sock_info, packet), 1)
			command = packet["header"]["command"]
			if self.WSHandlers is not None:
				if command in self.WSHandlers.keys():
					message = self.WSHandlers[command](sock, packet)
					if message == "" or message is None:
						return
					packet["payload"] = message
					self.Locker.acquire()
					self.Network.Send(sock_info["ip"], sock_info["port"], json.dumps(packet))
					time.sleep(0.1)
					self.Locker.release()
		except Exception as e:
			co_logger.LOGGER.Log("MKSDataArrivedHandler ({}) Exception: {} \n=======\nTrace: {}=======".format(command, str(e), traceback.format_exc()), 1)
			self.Locker.release()
	
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
		
		try:
			self.Locker.acquire()
			for sock in self.Network.Hive.SockMap:
				sock_info = self.Network.Hive.SockMap[sock]
				if sock != self.Network.Hive.ServerSocket:
					sock_info = self.Network.GetSocketInfoBySock(sock)
					self.Network.Send(sock_info["ip"], sock_info["port"], json.dumps(request))
			self.Locker.release()
		except:
			self.Locker.release()