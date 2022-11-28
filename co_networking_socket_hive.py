import time
import traceback

from core import co_security
from core import co_queue
from core import co_logger

class SocketHive():
	def __init__(self, server):
		self.NetworkServer 				= server
		self.SocketQueue 				= co_queue.Manager(self.SocketQueueHandler)
		self.OpenConnections 			= {}
		self.SockMap					= {}

		self.SocketDataArrivedCallback 	= None
		self.SocketClosedCallback 		= None
		self.SocketCreatedCallback 		= None
	
	def GetHash(self, ip, port):
		hashes = co_security.Hashes()
		return hashes.GetHashMd5("{0}_{1}".format(ip,str(port)))
	
	def EnhiveSocket(self, sock, ip, port, type, callback):
		hashes = co_security.Hashes()
		hash_key = hashes.GetHashMd5("{0}_{1}".format(ip,str(port)))
		if hash_key in self.OpenConnections:
			return None
		
		data = {
			"socket": 	sock,
			"ip": 		ip,
			"port": 	port,
			"hash": 	hash_key,
			"stream": 	bytes(),
			"type":		type,
			"timestamp": {
				"created": time.time(),
				"last_updated": time.time()
			}
		}

		self.OpenConnections[hash_key] = {
			"data": data,
			"callback": callback
		}

		self.SockMap[sock] = hash_key
		self.NetworkServer.RecievingSockets.append(sock)

		return hash_key

	def DehiveSocket(self, ip, port):
		hashes = co_security.Hashes()
		hash_key = hashes.GetHashMd5("{0}_{1}".format(ip,str(port)))
		if hash_key in self.OpenConnections:
			sock_info = self.OpenConnections[hash_key]
			if sock_info is None:
				return False
			
			sock = sock_info["data"]["socket"]
			# Remove socket from list.
			if sock is not None:
				if sock in self.NetworkServer.RecievingSockets:
					self.NetworkServer.RecievingSockets.remove(sock)			
				sock.close()
			try:
				if hash_key in self.OpenConnections:
					del self.OpenConnections[hash_key]
				if sock_info["data"]["socket"] in self.SockMap:
					del self.SockMap[sock_info["data"]["socket"]]
			except Exception as e:
				co_logger.LOGGER.Log("DehiveSocket Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
