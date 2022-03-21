
import json
import time
import socket
import _thread

from core.mks import mks_config
from core import co_definitions
from core import co_security
from core import co_logger

class UDPBroadcaster(co_definitions.ILayer):
	def __init__(self):
		co_definitions.ILayer.__init__(self)
		self.Config 				= mks_config.NodeConfig()
		self.ServerSocket			= None
		self.Network				= None
		self.DataSize				= 1024
		self.Port 					= 0
		self.ServerRunning 			= True
		self.DataArrivedEventQueue 	= None

		self.AmISlave				= False
		self.NodesList				= {}
		self.MasterTimeoutCount		= 0
	
	def Run(self):
		_thread.start_new_thread(self.ServerThread, ())
	
	def Stop(self):
		self.ServerRunning = False
	
	def AcqureMasterOwnership(self):
		co_logger.LOGGER.Log("Trying to acqure master ownership", 1)
		self.AmISlave = False
		self.MasterTimeoutCount = 0
		self.Port = self.Config.Application["server"]["broadcast"]["port"]
		self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			self.ServerSocket.bind(('', self.Port))
			co_logger.LOGGER.Log("I am master", 1)
		except:
			# Port is taken must be one of the nodes allready running
			self.AmISlave = True
			self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			co_logger.LOGGER.Log("I am slave", 1)
	
	def CheckDisconnectedNodes(self):
		del_nodes = []
		for key in self.NodesList:
			nodes = self.NodesList[key]
			if time.time() - int(nodes["timestamp"]["last_updated"]) > 20:
				del_nodes.append(key)
		for key in del_nodes:
			del self.NodesList[key]
	
	def ServerThread(self):
		status = self.Config.Load()
		if status is False:
			return
		
		splited_data = self.Config.LocalIPAddress.split('.')
		self.Network = "{}.{}.{}".format(splited_data[0], splited_data[1], splited_data[2])
		self.AcqureMasterOwnership()

		co_logger.LOGGER.Log("(UDPBroadcaster)# Start service ({0})".format(self.Port), 1)
		while self.ServerRunning is True:
			try:
				if self.AmISlave is False:
					data, addr = self.ServerSocket.recvfrom(self.DataSize)
					info = json.loads(data)

					if "request" in info:
						self.ServerSocket.sendto(str.encode(json.dumps(self.NodesList)), addr)
					else:
						ip 		 			= info["server"]["address"]["ip"]
						port 	 			= info["server"]["socket"]["port"]
						hash_key 			= co_security.Hashes().GetHashMd5("{0}_{1}".format(ip,str(port)))
						info["timestamp"] 	= {
							"last_updated": time.time()
						}
						self.NodesList[hash_key] = info
						# Check if DB has timeout nodes
						self.CheckDisconnectedNodes()

						if self.DataArrivedEventQueue is not None:
							self.DataArrivedEventQueue.QueueItem({
								"data": json.loads(data),
								"sender": {
									"ip": addr[0],
									"port": addr[1]
								}
							})
				else:
					# Polling the master
					buffer = str.encode(json.dumps({
						"request": "list"
					}))

					self.ServerSocket.sendto(buffer, ('localhost', self.Port))
					self.ServerSocket.settimeout(5)
					try:
						data = self.ServerSocket.recv(self.DataSize)
						time.sleep(5)
					except:
						# Master did not answered (3X times and we will try to acqure master ownership)
						if self.MasterTimeoutCount > 2:
							self.AcqureMasterOwnership()
						else:
							self.MasterTimeoutCount += 1

					if self.DataArrivedEventQueue is not None:
						items = json.loads(data)
						for key in items:
							item = items[key]
							self.DataArrivedEventQueue.QueueItem({
								"data": item,
								"sender": {
									"ip": item["server"]["address"]["ip"],
									"port": item["server"]["socket"]["port"]
								}
							})
			except Exception as e:
				co_logger.LOGGER.Log("(ServerThread)# {0}".format(str(e)), 1)
	
	def Send(self, data):
		buffer = str.encode(data)
		for idx in range(32):
			ip_addr = "{}.{}".format(self.Network, str(idx+1))
			clent_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			# print("Send BEACON")
			clent_socket.sendto(buffer, (ip_addr, self.Port))
		return True
	
	def RegisterEventQueue(self, e_queue):
		self.DataArrivedEventQueue = e_queue
