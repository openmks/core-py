import time
import json
import _thread
import socket
import struct
from core.mks import mks_config
from core import co_definitions
from core import co_queue
from core import co_security

class Multicaster(co_definitions.ILayer):
	def __init__(self):
		co_definitions.ILayer.__init__(self)
		self.Config 				= mks_config.NodeConfig()
		self.ServerSocket			= None
		self.ClientSocket  			= None
		self.DataSize				= 1024
		self.Port 					= 0
		self.ServerRunning 			= True
		self.DataArrivedEventQueue 	= None
	
	def Run(self):
		_thread.start_new_thread(self.ServerThread, ())
	
	def Stop(self):
		self.ServerRunning = False

	def ServerThread(self):
		status = self.Config.Load()
		if status is False:
			return
		
		self.Port = self.Config.Application["server"]["broadcast"]["port"]

		MULTICAST_TTL = 2
		self.ClientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.ClientSocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)

		self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.ServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.ServerSocket.bind(('', self.Port))

		MCAST_GRP = '224.1.1.1'
		mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
		self.ServerSocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

		print("(Multicaster)# Start service ({0})".format(self.Port))
		while self.ServerRunning is True:
			try:
				data, addr = self.ServerSocket.recvfrom(self.DataSize)
				if self.DataArrivedEventQueue is not None:
					self.DataArrivedEventQueue.QueueItem({
						"data": json.loads(data),
						"sender": {
							"ip": addr[0],
							"port": addr[1]
						}
					})
			except Exception as e:
				print("(ServerThread)# {0}".format(str(e)))
	
	def Send(self, data):
		buffer = str.encode(data)
		if self.ClientSocket is not None:
			self.ClientSocket.sendto(buffer, ('224.1.1.1', self.Port))
		return True
	
	def RegisterEventQueue(self, e_queue):
		self.DataArrivedEventQueue = e_queue

class MulticasterUsers():
	def __init__(self):
		self.Users 				= {}
		self.MulticastIn		= co_queue.Manager(self.MulticastData)
		self.Multicast 			= None
		self.Running 			= True
		self.MyInfo				= None
		self.UserEventsCallback	= None
		self.SecTicker			= 0
	
	def MulticastData(self, info):
		hash_key = info["data"]["hash"]
		if hash_key == self.Multicast.Config.Hash:
			return
		
		event_name 	= "update"
		ip 		 	= info["sender"]["ip"]
		port 	 	= info["data"]["server"]["socket"]["port"]
		hash_key 	= co_security.Hashes().GetHashMd5("{0}_{1}".format(ip,str(port)))
		# print("(MulticastData)# {0}:{1} ({2})".format(ip, port, hash_key))
		info["timestamp"] = {
			"last_updated": time.time()
		}
		if hash_key not in self.Users:
			event_name = "new"
		self.Users[hash_key] = info
		if self.UserEventsCallback is not None:
			self.UserEventsCallback(event_name, info)
	
	def CheckDisconnectedUsers(self):
		del_users = []
		for key in self.Users:
			user = self.Users[key]
			if time.time() - int(user["timestamp"]["last_updated"]) > 20:
				ip 		 = user["sender"]["ip"]
				port 	 = user["data"]["server"]["socket"]["port"]
				hash_key = co_security.Hashes().GetHashMd5("{0}_{1}".format(ip,str(port)))
				# User disconnected
				# print("(MulticastData)# Timeout {0}:{1} ({2})".format(ip, port, hash_key))
				del_users.append(hash_key)
		for key in del_users:
			if self.UserEventsCallback is not None:
				self.UserEventsCallback("del", self.Users[key])
			del self.Users[key]
	
	def Beacon(self):
		multicast_msg = self.Multicast.Config.Application
		multicast_msg["hash"] = self.Multicast.Config.Hash
		self.Multicast.Send(json.dumps(multicast_msg))
	
	def Run(self):
		_thread.start_new_thread(self.Worker, ())

	def Stop(self):
		self.Running = False
		self.Multicast.Stop()

	def Worker(self):
		self.MulticastIn.Start()
		self.Multicast = Multicaster()
		self.Multicast.RegisterEventQueue(self.MulticastIn)
		self.Multicast.Run()

		while self.Running is True:
			self.SecTicker += 1
			if (self.SecTicker % 10) == 0:
				self.Beacon()
				self.CheckDisconnectedUsers()
			time.sleep(1)
	
	def GetUsers(self):
		return self.Users