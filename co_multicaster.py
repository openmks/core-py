import time
import json
import _thread
import socket
import struct

from core.mks import mks_config
from core import co_definitions

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
		# mreq = struct.pack("4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton("192.168.101.2"))
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
