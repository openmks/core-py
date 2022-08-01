import threading
import _thread
import time
import socket, select
import traceback

from core.mks import mks_config
from core import co_definitions
from core import co_security
from core import co_queue
from core import co_logger

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
		self.ListenningPort				= None

		self.SocketDataArrivedCallback 	= None
		self.SocketClosedCallback 		= None
		self.SocketCreatedCallback 		= None
	
	def Run(self, port):
		self.ListenningPort = port
		_thread.start_new_thread(self.ServerThread, ())
	
	def Stop(self):
		self.ServerRunning = False

	# Queue manager for this thread
	def SocketQueueHandler(self, item):
		if "new_sock" in item["type"]:
			hash_key = self.EnhiveSocket(item["data"]["sock"], item["data"]["ip"], item["data"]["port"], None)
			item["data"]["hash"] = hash_key
			if self.SocketCreatedCallback is not None:
				self.SocketCreatedCallback({
					"event": "new_sock",
					"event_data": item["data"]
				})
		elif "new_data" in item["type"]:
			sock = item["data"]["sock"]
			if sock not in self.SockMap:
				return
			sock_info = self.SockMap[sock]
			# Update TS for monitoring
			sock_info["data"]["timestamp"]["last_updated"] = time.time()
			# Append recieved data to the previuose portion
			sock_info["data"]["stream"] += item["data"]["data"]

			mks_data 		= sock_info["data"]["stream"]
			mks_data_len 	= len(sock_info["data"]["stream"])

			working = True
			while working is True:
				mkss_index 		= mks_data.find("MKSS".encode())
				mkse_index 		= mks_data.find("MKSE".encode())

				if mkss_index != -1 and mkse_index != -1:
					# Found MKS packet
					data = mks_data[mkss_index+4:mkse_index]
					# co_logger.LOGGER.Log("Networking (SocketEventHandler) PACKET.", 1)
					# Raise event for listeners
					if self.SocketDataArrivedCallback is not None:
						self.SocketDataArrivedCallback({
							"event": "new_data",
							"event_data": {
								"sock_info": sock_info,
								"data": data
							}
						})
					
					mks_data = mks_data[mkse_index+4:mks_data_len]
					sock_info["data"]["stream"] = mks_data
				else:
					# Did not found MKS packet
					# co_logger.LOGGER.Log("Networking (SocketEventHandler) NO MAGIC NUMBER IN PACKET.", 1)
					return
			
		elif "close_sock" in item["type"]:
			sock = item["data"]
			if sock not in self.SockMap:
				return
			sock_info = self.SockMap[sock]
			ip = sock_info["data"]["ip"]
			port = sock_info["data"]["port"]
			self.DehiveSocket(ip, port)
			if self.SocketClosedCallback is not None:
				self.SocketClosedCallback({
					"event": "close_sock",
					"event_data": sock_info["data"]
				})
		elif "send" in item["type"]:
			hash_key = item["data"]["hash"]
			data = item["data"]["data"]
			sock_info = self.OpenConnections[hash_key]
			#co_logger.LOGGER.Log("Send {} {}".format(type(data), "MKSS"+data+"MKSE"), 1)
			retry = 3
			while retry != 0:
				try:
					sock_info["data"]["socket"].send(("MKSS"+data+"MKSE").encode())
					return
				except Exception as e:
					co_logger.LOGGER.Log("SocketQueueHandler ({}, {}) Exception: {}".format(retry, len(data), str(e)), 1)
					retry -= 1
			
			if retry == 0:
				try:
					data_length		 = len(data)
					data_length_half = data_length/2
					sock_info["data"]["socket"].send(("MKSS"+data[0:data_length_half]+"MKSE").encode())
					sock_info["data"]["socket"].send(("MKSS"+data[data_length_half:data_length]+"MKSE").encode())
				except Exception as e:
					co_logger.LOGGER.Log("SocketQueueHandler HALF ({}) Exception: {}".format(len(data), str(e)), 1)
				
			#sock_info["data"]["socket"].send(data.encode())
	
	def EnhiveSocket(self, sock, ip, port, callback):
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
			"timestamp": {
				"created": time.time(),
				"last_updated": time.time()
			}
		}

		self.OpenConnections[hash_key] = {
			"data": data,
			"callback": callback
		}

		self.SockMap[sock] = {
			"data": data,
			"callback": callback
		}
		self.RecievingSockets.append(sock)

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
				if sock in self.RecievingSockets:
					self.RecievingSockets.remove(sock)
				
				if self.ServerSocket == sock:
					self.ListenningPort = None
			
				sock.close()
			try:
				if hash_key in self.OpenConnections:
					del self.OpenConnections[hash_key]
				if sock_info["data"]["socket"] in self.SockMap:
					del self.SockMap[sock_info["data"]["socket"]]
			except Exception as e:
				co_logger.LOGGER.Log("DehiveSocket Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)

	def ServerThread(self):
		status = self.Config.Load()
		if status is False:
			return
		
		self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ServerSocket.setblocking(0)
		self.ServerSocket.bind(('', self.ListenningPort))
		self.EnhiveSocket(self.ServerSocket, '', self.ListenningPort, None)
		self.ServerSocket.listen(32)
		self.SocketQueue.Start()

		co_logger.LOGGER.Log("ServerThread)# Start service ({0})".format(self.ListenningPort), 1)
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
									# co_logger.LOGGER.Log("Networking ({}) Data -> {}".format(len(data), data), 1)
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
							if sock in self.RecievingSockets:
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
				co_logger.LOGGER.Log("ServerThread Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
		
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
	def __init__(self, handlers, server_sock_open_callback, server_sock_data_arrived_callback, server_sock_close_callback):
		co_definitions.ILayer.__init__(self)
		self.Hive = SocketHive()
		self.Hive.SocketDataArrivedCallback = self.SocketDataArrivedHandler
		self.Hive.SocketClosedCallback 		= self.SocketClosedHandler
		self.Hive.SocketCreatedCallback		= self.SocketCreatedHandler
		self.DataArrivedEventQueue 			= co_queue.Manager(self.SocketEventHandler)
		
		self.Handlers = handlers
		self.Handlers["connect_neighbor"] 		= self.ConnectNeighborHandler
		self.Handlers["disconnect_neighbor"] 	= self.DisconnectNeighborHandler
		self.Handlers["send_data_to_neighbor"] 	= self.SendDataToNeighborHandler

		self.ServerSockOpenCallback 		= server_sock_open_callback
		self.ServerSockDataArrivedCallback 	= server_sock_data_arrived_callback
		self.ServerSockCloseCallback 		= server_sock_close_callback

		self.DataArrivedEventQueue.Start()
	
	def SetServerSockDataArrivedCallback(self, callback):
		co_logger.LOGGER.Log("Networking (SetServerSockDataArrivedCallback) {}".format(""), 1)
		self.ServerSockDataArrivedCallback = callback
	
	def SocketEventHandler(self, event):
		#co_logger.LOGGER.Log("Networking (SocketEventHandler) {0}".format(event), 1)
		server_socket 	= self.Hive.ServerSocket
		event_name 		= event["name"]
		event_data 		= event["data"]["event_data"]

		if "new" in event_name:
			co_logger.LOGGER.Log("Networking (SocketEventHandler) Open socket. {}".format(event_data), 1)
			if self.ServerSockOpenCallback is not None:
				self.ServerSockOpenCallback(event_data)
		elif "data" in event_name:
			sock_info 		= event_data["sock_info"]["data"]
			sock 			= sock_info["socket"]
			data			= event_data["data"]
			if sock == server_socket:
				if self.ServerSockDataArrivedCallback is not None:
					self.ServerSockDataArrivedCallback(sock, sock_info, data)
			else:
				client_callback = event_data["sock_info"]["callback"]
				if client_callback is not None:
					client_callback(sock, sock_info, data)
				else:
					if self.ServerSockDataArrivedCallback is not None:
						self.ServerSockDataArrivedCallback(sock, sock_info, data)
		elif "closed" in event_name:
			co_logger.LOGGER.Log("Networking (SocketEventHandler) Close socket. {}".format(event_data), 1)
			if self.ServerSockCloseCallback is not None:
				self.ServerSockCloseCallback(event_data)
		else:
			pass

	def ConnectNeighborHandler(self, sock, packet):
		hash = None
		if "payload" not in packet:
			return {
				"error": "No payload",
				"hash": hash
			}
		
		if "ip" not in packet["payload"]:
			return {
				"error": "No IP address",
				"hash": hash
			}
		
		if "port" not in packet["payload"]:
			return {
				"error": "No IP port",
				"hash": hash
			}
		
		ip 		= packet["payload"]["ip"]
		port 	= packet["payload"]["port"]

		try:
			hash = self.Connect(ip, port)
		except Exception as e:
			return {
				"error": str(e),
				"hash": hash
			}
			
		return {
			"error": "",
			"hash": hash
		}

	def DisconnectNeighborHandler(self, sock, packet):
		if "payload" not in packet:
			return {
				"error": "No payload"
			}
		
		if "ip" not in packet["payload"]:
			return {
				"error": "No IP address"
			}
		
		if "port" not in packet["payload"]:
			return {
				"error": "No IP port"
			}
		
		ip 		= packet["payload"]["ip"]
		port 	= packet["payload"]["port"]

		try:
			self.Disconnect(ip, port)
		except Exception as e:
			return {
				"error": str(e)
			}
			
		return {
			"error": ""
		}
	
	def SendDataToNeighborHandler(self, sock, packet):
		if "payload" not in packet:
			return {
				"error": "No payload"
			}
		
		if "ip" not in packet["payload"]:
			return {
				"error": "No IP address"
			}
		
		if "port" not in packet["payload"]:
			return {
				"error": "No IP port"
			}
		
		if "data" not in packet["payload"]:
			return {
				"error": "No data"
			}
		
		ip 		= packet["payload"]["ip"]
		port 	= packet["payload"]["port"]
		data 	= packet["payload"]["data"]

		try:
			status = self.Send(ip, port, data)
		except Exception as e:
			return {
				"error": str(e),
				"status": status
			}
			
		return {
			"error": "",
			"status": status
		}
	
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

	def Run(self, port):
		co_logger.LOGGER.Log("Networking (Run) {}".format(port), 1)
		self.Hive.Run(port)
	
	def Stop(self):
		co_logger.LOGGER.Log("Networking (Stop) {}".format(""), 1)
		self.Hive.Stop()

	def Connect(self, ip, port, callback):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(5)
		try:
			sock.connect((ip, port))
			hash_key = self.Hive.EnhiveSocket(sock, ip, port, callback)
			co_logger.LOGGER.Log("Networking (Connect) {} {} SUCCESS".format(ip, port), 1)
			return hash_key
		except Exception as e:
			co_logger.LOGGER.Log("Networking (Connect) {} {} FAILED\n{}".format(ip, port,e), 1)
			return None
		
	def Disconnect(self, ip, port):
		co_logger.LOGGER.Log("Networking (Disconnect) {} {}".format(ip, port), 1)
		self.Hive.DehiveSocket(ip, port)
	
	def Send(self, ip, port, data):
		# co_logger.LOGGER.Log("Networking (Send) {} {}".format(ip, port), 1)
		return self.Hive.Send(ip, port, data)

	def GetSocketInfoBySock(self, sock):
		if sock in self.Hive.SockMap:
			return self.Hive.SockMap[sock]["data"]

		return None

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
	