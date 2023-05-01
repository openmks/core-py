import threading
import _thread
import time
import socket, select
import traceback

import zlib as zl
from core.mks import mks_config
from core import co_definitions
from core import co_security
from core import co_queue
from core import co_logger

class SocketHive():
	def __init__(self):
		__slots__ = (	'Config', 'LocSocketQueueker', 'ServerSocket', 'RecievingSockets',
		 				'SendingSockets', 'OpenConnections', 'SockMap', 'ServerRunning',
		 				'ListenningPort', 'SocketDataArrivedCallback', 'SocketClosedCallback', 'SocketCreatedCallback', 'CHUNK_SIZE')
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

		self.CHUNK_SIZE = 65536
	
	def Run(self, port):
		self.ListenningPort = port
		_thread.start_new_thread(self.ServerThread, ())
	
	def Stop(self):
		self.ServerRunning = False

	# Queue manager for this thread
	def SocketQueueHandler(self, item):
		if "new_sock" in item["type"]:
			# print(item["data"]["sock"].getsockname())
			hash_key = self.EnhiveSocket(item["data"]["sock"], item["data"]["ip"], item["data"]["port"], "IN", None)
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
				mkss_index = mks_data.find("MKSS".encode())
				mkse_index = mks_data.find("MKSE".encode())

				#co_logger.LOGGER.Log("R: {}".format(mks_data_len), 1)
				if mkss_index != -1 and mkse_index != -1:
					# Found MKS packet
					data = mks_data[mkss_index+4:mkse_index]

					#if len(data) > self.CHUNK_SIZE:
					try:
						# co_logger.LOGGER.Log("R: {}".format(len(data)), 1)
						decoded_data_str = data.decode()
						# create bytes object from a string
						decoded_data_byt = bytes.fromhex(decoded_data_str)
						data = zl.decompress(decoded_data_byt)
						# co_logger.LOGGER.Log("SocketQueueHandler (RX) {}".format(len(data)), 1)
					except Exception as e:
						co_logger.LOGGER.Log("SocketQueueHandler (ZL) Exception: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
					
					#co_logger.LOGGER.Log("R (D): {}".format(mks_data_len), 1)
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
					break
				else:
					# Did not found MKS packet
					break
			#co_logger.LOGGER.Log("R: (E) {}".format(mks_data_len), 1)
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
			hash_key 	= item["data"]["hash"]
			data 		= item["data"]["data"]
			sock_info 	= self.OpenConnections[hash_key]
			index_db = 0
			num_of_chuncks = 0
			try:
				#if len(data) > self.CHUNK_SIZE:
				if type(data) is bytes:
					data = zl.compress(data, zl.Z_BEST_COMPRESSION).hex()
				else:
					data = zl.compress(data.encode(), zl.Z_BEST_COMPRESSION).hex()
					
				data_length		= len(data)
				chunck_size 	= self.CHUNK_SIZE
				num_of_chuncks 	= int(data_length / chunck_size)

				if num_of_chuncks == 0:
					sock_info["data"]["socket"].send(("MKSS"+data+"MKSE").encode())
				else:
					for idx in range(num_of_chuncks):
						index_db = idx
						if idx == 0:
							sock_info["data"]["socket"].send(("MKSS"+data[idx * chunck_size:(idx + 1) * chunck_size]).encode())
						else:
							sock_info["data"]["socket"].send((data[idx * chunck_size:(idx + 1) * chunck_size]).encode())
						time.sleep(0.1)
					left_over = data_length % chunck_size
					sock_info["data"]["socket"].send((data[data_length-left_over:data_length]+"MKSE").encode())
			except Exception as e:
				co_logger.LOGGER.Log("SocketQueueHandler [SEND] ({}/{}) ({}) Exception: {}".format(index_db, num_of_chuncks, len(data), str(e)), 1)
	
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
		self.EnhiveSocket(self.ServerSocket, '', self.ListenningPort, "SERVER", None)
		self.ServerSocket.listen(32)
		self.SocketQueue.Start()

		co_logger.LOGGER.Log("ServerThread)# Start service ({0})".format(self.ListenningPort), 1)
		while self.ServerRunning is True:
			try:
				read, write, exc = select.select(self.RecievingSockets, self.SendingSockets, self.RecievingSockets, 0.5)
				for sock in read:
					if sock is self.ServerSocket:
						conn, addr = sock.accept()
						conn.setblocking(0)
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
								data = sock.recv(self.CHUNK_SIZE)
								#dataLen = len(data)
								#while dataLen == 65536:
								#	chunk = sock.recv(65536)
								#	data += chunk
								#	dataLen = len(chunk)
								#	co_logger.LOGGER.Log("Chunk {}".format(len(chunk)), 1)
								if data:
									# co_logger.LOGGER.Log("Networking ({}) Data -> {}".format(len(data), data), 1)
									# Append to new data queue
									# co_logger.LOGGER.Log("Data {}".format(len(data)), 1)
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
	
	def SetServerSockOpenCallback(self, callback):
		co_logger.LOGGER.Log("Networking (SetServerSockOpenCallback)", 1)
		self.ServerSockOpenCallback = callback
	
	def SetServerSockDataArrivedCallback(self, callback):
		co_logger.LOGGER.Log("Networking (SetServerSockDataArrivedCallback)", 1)
		self.ServerSockDataArrivedCallback = callback
	
	def SetServerSockClosedCallback(self, callback):
		co_logger.LOGGER.Log("Networking (SetServerSockClosedCallback)", 1)
		self.ServerSockCloseCallback = callback
	
	def SocketEventHandler(self, event):
		server_socket 	= self.Hive.ServerSocket
		event_name 		= event["name"]
		event_data 		= event["data"]["event_data"]

		if "new" in event_name:
			# co_logger.LOGGER.Log("Networking (SocketEventHandler) Open socket. {}".format(event_data), 1)
			if self.ServerSockOpenCallback is not None:
				self.ServerSockOpenCallback(event_data)
		elif "data" in event_name:
			sock_info 		= event_data["sock_info"]["data"]
			sock 			= sock_info["socket"]
			data			= event_data["data"]
			if sock == server_socket:
				# co_logger.LOGGER.Log("Networking (SocketEventHandler) Server Data - {}".format(event_data), 1)
				if self.ServerSockDataArrivedCallback is not None:
					self.ServerSockDataArrivedCallback(sock, sock_info, data)
			else:
				# co_logger.LOGGER.Log("Networking (SocketEventHandler) Client Data - {}".format(event_data), 1)
				client_callback = event_data["sock_info"]["callback"]
				if client_callback is not None:
					client_callback(sock, sock_info, data)
				else:
					# co_logger.LOGGER.Log("Networking (SocketEventHandler) Server #2 Data - {}".format(event_data), 1)
					if self.ServerSockDataArrivedCallback is not None:
						self.ServerSockDataArrivedCallback(sock, sock_info, data)
		elif "closed" in event_name:
			# co_logger.LOGGER.Log("Networking (SocketEventHandler) Close socket. {}".format(event_data), 1)
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
			hash = self.Connect(ip, port, None)
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
		sock.settimeout(2)
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
	
	def Send(self, ip, port, data):
		# co_logger.LOGGER.Log("Networking (Send) {} {}".format(ip, port), 1)
		return self.Hive.Send(ip, port, data)
	
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
			conn = {
				"ip": connection["data"]["ip"],
				"port": connection["data"]["port"],
				"hash": connection["data"]["hash"],
				"type": connection["data"]["type"]
			}
			if "config" in connection:
				conn["mks"] = {
					"web": connection["config"]["application"]["server"]["web"],
					"web_socket": connection["config"]["application"]["server"]["web_socket"],
					"socket": connection["config"]["application"]["server"]["socket"]
				}
			connections.append(conn)
		return connections
	
	def HiveStatistics(self):
		info = {
			"Sockets": {
				"RX": 	len(self.Hive.RecievingSockets),
				"TX": 	len(self.Hive.SendingSockets),
				"Open": len(self.Hive.OpenConnections)
			}
		}
		return info
	