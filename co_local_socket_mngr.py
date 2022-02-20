import threading
import _thread
import time
import socket, select

from core.mks import mks_config
from core import co_definitions
from core import co_security
from core import co_queue

class SocketHive():
	def __init__(self):
		self.Config 					= mks_config.NodeConfig()
		self.SocketQueue 				= co_queue.Manager(self.SocketQueueHandler)
		self.ServerSocket 				= None
		self.RecievingSockets			= []
		self.SendingSockets				= []
		self.OpenConnections 			= {}
		self.SockMap					= {}
		self.ServerRunning				= True

		self.SocketDataArrivedCallback 	= None
		self.SocketClosedCallback 		= None
		self.SocketCreatedCallback 		= None
	
	def Run(self):
		_thread.start_new_thread(self.ServerThread, ())
	
	def Stop(self):
		self.ServerRunning = False

	def SocketQueueHandler(self, item):
		if "new_sock" in item["type"]:
			self.EnhiveSocket(item["data"]["sock"], item["data"]["ip"], item["data"]["port"])
			if self.SocketCreatedCallback is not None:
				self.SocketCreatedCallback(item["data"])
		elif "new_data" in item["type"]:
			sock = item["data"]["sock"]
			if sock not in self.SockMap:
				return
			sock_info = self.SockMap[sock]
			# Update TS for monitoring
			sock_info["timestamp"]["last_updated"] = time.time()
			# Raise event for listeners
			if self.SocketDataArrivedCallback is not None:
				self.SocketDataArrivedCallback({
					"sock_info": sock_info,
					"data": item["data"]["data"]
				})
		elif "close_sock" in item["type"]:
			sock = item["data"]
			if sock not in self.SockMap:
				return
			sock_info = self.SockMap[sock]
			ip = sock_info["ip"]
			port = sock_info["port"]
			self.DehiveSocket(ip, port)
			if self.SocketClosedCallback is not None:
				self.SocketClosedCallback({
					"ip": ip,
					"port": port
				})
		elif "send" in item["type"]:
			hash_key = item["data"]["hash"]
			data = item["data"]["data"]
			sock_info = self.OpenConnections[hash_key]
			sock_info["socket"].send(data.encode())
	
	def EnhiveSocket(self, sock, ip, port):
		hashes = co_security.Hashes()
		hash_key = hashes.GetHashMd5("{0}_{1}".format(ip,str(port)))
		if hash_key in self.OpenConnections:
			return None
		
		data = {
			"socket": 	sock,
			"ip": 		ip,
			"port": 	port,
			"hash": 	hash_key,
			"timestamp": {
				"created": time.time(),
				"last_updated": time.time()
			}
		}

		self.OpenConnections[hash_key] = data
		self.SockMap[sock] = data
		self.RecievingSockets.append(sock)

		return hash_key

	def DehiveSocket(self, ip, port):
		hashes = co_security.Hashes()
		hash_key = hashes.GetHashMd5("{0}_{1}".format(ip,str(port)))
		if hash_key in self.OpenConnections:
			sock_info = self.OpenConnections[hash_key]
			if sock_info is None:
				return False
			
			sock = sock_info["socket"]
			# Remove socket from list.
			if sock is not None:
				if sock in self.RecievingSockets:
					self.RecievingSockets.remove(sock)
			
				sock.close()
			
			del self.OpenConnections[hash_key]
			del self.SockMap[sock_info["socket"]]

	def ServerThread(self):
		status = self.Config.Load()
		if status is False:
			return
		
		port = self.Config.Application["server"]["socket"]["port"]
		self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ServerSocket.setblocking(0)
		self.ServerSocket.bind(('', port))
		self.EnhiveSocket(self.ServerSocket, '', port)
		self.ServerSocket.listen(32)
		self.SocketQueue.Start()

		print("(ServerThread)# Start service ({0})".format(port))
		while self.ServerRunning is True:
			try:
				read, write, exc = select.select(self.RecievingSockets, self.SendingSockets, self.RecievingSockets, 0.5)
				for sock in read:
					if sock is self.ServerSocket:
						conn, addr = sock.accept()
						# conn.setblocking(0)
						# Append to new socket queue
						self.SocketQueue.QueueItem({
							"type": "new_sock",
							"data": {
								"sock": conn,
								"ip": addr[0],
								"port": addr[1]
							}
						})
					else:
						try:
							if sock is not None:
								data = sock.recv(2048)
								dataLen = len(data)
								while dataLen == 2048:
									chunk = sock.recv(2048)
									data += chunk
									dataLen = len(chunk)
								if data:
									# Append to new data queue
									self.SocketQueue.QueueItem({
										"type": "new_data",
										"data": {
											"sock": sock,
											"data": data
										}
									})
								else:
									# Remove socket from list.
									self.RecievingSockets.remove(sock)
									# Append to socket disconnected queue
									self.SocketQueue.QueueItem({
										"type": "close_sock",
										"data": sock
									})
							else:
								pass
						except Exception as e:
							# Remove socket from list.
							self.RecievingSockets.remove(sock)
							# Append to socket disconnected queue
							self.SocketQueue.QueueItem({
								"type": "close_sock",
								"data": sock
							})
				for sock in write:
					pass
				for sock in exc:
					pass
			except Exception as e:
				print("(ServerThread)# {0}".format(str(e)))
		
		# TODO - Close everything
	
	def Send(self, ip, port, data):
		hashes = co_security.Hashes()
		hash_key = hashes.GetHashMd5("{0}_{1}".format(ip,str(port)))

		if hash_key not in self.OpenConnections:
			return False

		self.SocketQueue.QueueItem({
			"type": "send",
			"data": {
				"hash": hash_key,
				"data": data
			}
		})

		return True

class Networking(co_definitions.ILayer):
	def __init__(self):
		co_definitions.ILayer.__init__(self)
		self.Hive = SocketHive()
		self.Hive.SocketDataArrivedCallback = self.SocketDataArrivedHandler
		self.Hive.SocketClosedCallback = self.SocketClosedHandler
		self.Hive.SocketCreatedCallback	= self.SocketCreatedHandler
		self.DataArrivedEventQueue = None
	
	def SocketCreatedHandler(self, data):
		if self.DataArrivedEventQueue is not None:
			self.DataArrivedEventQueue.QueueItem({
				"name": "new",
				"data": data
			})

	def SocketClosedHandler(self, data):
		if self.DataArrivedEventQueue is not None:
			self.DataArrivedEventQueue.QueueItem({
				"name": "closed",
				"data": data
			})
	
	def SocketDataArrivedHandler(self, data):
		if self.DataArrivedEventQueue is not None:
			self.DataArrivedEventQueue.QueueItem({
				"name": "data",
				"data": data
			})

	def Run(self):
		self.Hive.Run()
	
	def Stop(self):
		self.Hive.Stop()

	def Connect(self, ip, port):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(5)
		try:
			sock.connect((ip, port))
			hash_key = self.Hive.EnhiveSocket(sock, ip, port)
			return hash_key
		except:
			return None
		
	def Disconnect(self, ip, port):
		self.Hive.DehiveSocket(ip, port)
	
	def Send(self, ip, port, data):
		return self.Hive.Send(ip, port, data)

	def GetConnectionInfo(self, hash_key):
		if hash_key not in self.Hive.OpenConnections:
			return None
		
		return self.Hive.OpenConnections[hash_key]
	
	def HiveStatistics(self):
		info = {
			"Sockets": {
				"RX": 	len(self.Hive.RecievingSockets),
				"TX": 	len(self.Hive.SendingSockets),
				"Open": len(self.Hive.OpenConnections)
			}
		}
		return info
	
	def RegisterEventQueue(self, e_queue):
		self.DataArrivedEventQueue = e_queue
	