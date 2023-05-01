import json
import traceback
import time
import orjson

from core import co_logger
from core import co_async_block
from core import co_queue

import threading

class MKSSocket():
	def __init__(self, network, handlers):
		self.Network 		= network
		self.Socket 		= None
		self.WSHandlers		= handlers
		self.Locker 		= threading.Lock()
		self.SocketQueue	= co_queue.Manager(self.MessageQueueHandler)
		self.SocketQueue.Start()

		self.ServerSockOpenCallback 		= None
		self.ServerSockDataArrivedCallback 	= None
		self.ServerSockCloseCallback 		= None
	
	def SetServerSockOpenCallback(self, callback):
		co_logger.LOGGER.Log("MKSSocket (SetServerSockOpenCallback)", 1)
		self.ServerSockOpenCallback = callback
	
	def SetServerSockDataArrivedCallback(self, callback):
		co_logger.LOGGER.Log("MKSSocket (SetServerSockDataArrivedCallback)", 1)
		self.ServerSockDataArrivedCallback = callback
	
	def SetServerSockClosedCallback(self, callback):
		co_logger.LOGGER.Log("MKSSocket (SetServerSockClosedCallback)", 1)
		self.ServerSockCloseCallback = callback
	
	def MessageQueueHandler(self, msg):
		# co_logger.LOGGER.Log("MessageQueueHandler {}".format(msg), 1)
		msg_type = msg["type"]
		msg_data = msg["data"]
		if "enhive" in msg_type:
			ip 	 = msg_data["ip"]
			port = msg_data["port"]
			hash = msg_data["hash"]
			sock = msg_data["sock"]

			tunnel = co_async_block.AsyncBlock(self.Network, ip, port)
			tunnel.Hash = hash
			request = {
				"header": {
					"command": "get_config",
					"timestamp": time.time(),
					"identifier": 0
				},
				"payload": {}
			}

			time.sleep(0.5)
			if sock.fileno() == -1:
				return
			
			hash_key = self.Network.Hive.GetHash(ip, port)
			# Invalid code ->
			self.Network.Hive.OpenConnections[hash_key]["callback"] = tunnel.Callback
			self.Network.Hive.SockMap[sock]["callback"] = tunnel.Callback
			# Invalid code <-
			
			self.Locker.acquire()
			# Will block Networking.SocketEventHandler method (no data will be sent or arrived)
			# tunnel.SignalTimeout = 1.0
			resp = tunnel.Execute(request)
			# tunnel.SignalTimeout = 8.0
			co_logger.LOGGER.Log("MKSEnhiveSocketHandler - GET_CONFIG {} -> {}".format(hash, resp), 1)
			# Invalid code ->
			try:
				if resp is not None:
					if "config" in resp:
						self.Network.Hive.OpenConnections[hash_key]["config"] = resp["config"]
						self.Network.Hive.SockMap[sock]["config"] = resp["config"]
						if self.ServerSockOpenCallback is not None:
							self.ServerSockOpenCallback({
								"ip": ip,
								"port": port,
								"hash": hash,
								"sock": sock,
								"config": resp["config"]
							})
							self.Locker.release()
							return
			# Invalid code <-
			except:
				pass

			self.Locker.release()
			if self.ServerSockOpenCallback is not None:
				self.ServerSockOpenCallback(msg_data)
		elif "async_send" in msg_type:
			event_name = msg["event_name"]
			request = {
				"header": {
					"command": "event",
					"timestamp": time.time(),
					"identifier": 0
				},
				"payload": {
					"event": event_name,
					"data": msg_data
				}
			}
			
			try:
				for sock in self.Network.Hive.SockMap:
					sock_info = self.Network.Hive.SockMap[sock]
					if sock != self.Network.Hive.ServerSocket:
						sock_info = self.Network.GetSocketInfoBySock(sock)
						raw_request = orjson.dumps(request)
						self.Network.Send(sock_info["ip"], sock_info["port"], raw_request)
			except:
				pass
		else:
			pass

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
					'last_updated': 1659274757.1712267
				}
			}
			'''
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
			if self.Locker.locked() is True:
				self.Locker.release()
		
		if self.ServerSockDataArrivedCallback is not None:
			self.ServerSockDataArrivedCallback(sock, sock_info, data)
	
	def MKSEnhiveSocketHandler(self, data):
		self.SocketQueue.QueueItem({
			"type": "enhive",
			"data": data
		})
	
	def MKSDehiveSocketHandler(self, sock_info):
		co_logger.LOGGER.Log("MKSDehiveSocketHandler {}".format(sock_info), 1)
		if self.ServerSockCloseCallback is not None:
			self.ServerSockCloseCallback(sock_info)
	
	def Run(self):
		self.Network.SetServerSockDataArrivedCallback(self.MKSDataArrivedHandler)
		self.Network.SetServerSockOpenCallback(self.MKSEnhiveSocketHandler)
		self.Network.SetServerSockClosedCallback(self.MKSDehiveSocketHandler)
	
	def AsyncSend(self, event_name, data):
		#self.SocketQueue.QueueItem({
		#	"type": "async_send",
		#	"event_name": event_name,
		#	"data": data
		#})
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
					raw_request = orjson.dumps(request)
					self.Network.Send(sock_info["ip"], sock_info["port"], raw_request)
			self.Locker.release()
		except Exception as e:
			co_logger.LOGGER.Log("AsyncSend [SEND] ({}) Exception: {}".format(len(data), str(e)), 1)
			if self.Locker.locked() is True:
				self.Locker.release()