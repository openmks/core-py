import _thread
import socket, select
import traceback

from core import co_logger
from core import co_networking_socket_hive

class NetworkServer():
	def __init__(self, network_handler):
		self.ServerSocket 				= None
		self.RecievingSockets			= []
		self.SendingSockets				= []
		self.ServerRunning				= True
		self.ListenningPort				= None
		self.ListenningLimit 			= 32
		self.NetHandler 				= network_handler
		self.Hive 						= co_networking_socket_hive.SocketHive(self)
	
	def Run(self, port, limit):
		if self.NetHandler is None:
			return False
		
		self.ListenningPort  = port
		self.ListenningLimit = limit
		_thread.start_new_thread(self.ServerThread, ())
		return True

	def Pause(self):
		pass

	def Stop(self):
		self.ServerRunning = False

	def ServerThread(self):		
		self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# Set blocking or non-blocking mode of the socket: if flag is false, the socket is set to non-blocking, else to blocking mode.
		# sock.setblocking(True) is equivalent to sock.settimeout(None)
		# sock.setblocking(False) is equivalent to sock.settimeout(0.0)
		self.ServerSocket.setblocking(0) 
		self.ServerSocket.bind(('', self.ListenningPort))
		self.ServerSocket.listen(self.ListenningLimit)

		co_logger.LOGGER.Log("ServerThread)# Start service ({0})".format(self.ListenningPort), 1)
		while self.ServerRunning is True:
			try:
				read, write, exc = select.select(self.RecievingSockets, self.SendingSockets, self.RecievingSockets, 0.5)
				for sock in read:
					if sock is self.ServerSocket:
						conn, addr = sock.accept()
						# conn.setblocking(0)
						# Append to new socket queue
						self.NetHandler.PushMessage({
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
									self.NetHandler.PushMessage({
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
									self.NetHandler.PushMessage({
										"type": "close_sock",
										"data": sock
									})
							else:
								pass
						except Exception as e:
							# Remove socket from list.
							if sock in self.RecievingSockets:
								self.RecievingSockets.remove(sock)
							# Append to socket disconnected queue
							self.NetHandler.PushMessage({
								"type": "close_sock",
								"data": sock
							})
				for sock in write:
					pass
				for sock in exc:
					pass
			except Exception as e:
				co_logger.LOGGER.Log("ServerThread <Exception>: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)

	def Send(self, sock, data):
		self.NetHandler.PushMessage({
			"type": "send_sock",
			"data": {
				"sock": sock,
				"stream": data
			}
		})
	
	def Connect(self, ip ,port, callback):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(5)
		try:
			sock.connect((ip, port))
			hash_key = self.Hive.EnhiveSocket(sock, ip, port, "OUT", callback)
			# co_logger.LOGGER.Log("Networking (Connect) {} {} SUCCESS".format(ip, port), 1)
			return hash_key
		except Exception as e:
			# co_logger.LOGGER.Log("Networking (Connect) {} {} FAILED\n{}".format(ip, port,e), 1)
			return None
	
	def Disconnect(self, ip, port):
		co_logger.LOGGER.Log("Networking (Disconnect) {} {}".format(ip, port), 1)
		self.Hive.DehiveSocket(ip, port)
	
	def GetSocketInfoByIpPort(self, ip, port):
		hash_key = self.Hive.GetHash(ip, port)
		return self.GetConnectionInfo(hash_key)

	def GetSocketInfoBySock(self, sock):
		if sock in self.Hive.SockMap:
			return self.Hive.SockMap[sock]["data"]

		return None

	def GetConnectionInfo(self, hash_key):
		if hash_key not in self.Hive.OpenConnections:
			return None
		
		return self.Hive.OpenConnections[hash_key]
	
	def GetConnectionList(self):
		'''
		{
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
		'''
		connections = []
		for key in self.Hive.OpenConnections:
			connection = self.Hive.OpenConnections[key]
			connections.append({
				"ip": connection["data"]["ip"],
				"port": connection["data"]["port"],
				"hash": connection["data"]["hash"],
				"type": connection["data"]["type"]
			})
		return connections
	
	def HiveStatistics(self):
		info = {
			"Sockets": {
				"RX": 	len(self.RecievingSockets),
				"TX": 	len(self.SendingSockets),
				"Open": len(self.Hive.OpenConnections)
			}
		}
		return info