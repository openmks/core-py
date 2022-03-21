import time
import json
import _thread

from core import co_queue
from core import co_security

class Beaconer():
	def __init__(self, ILayer):
		self.Users 				= {}
		self.MulticastIn		= co_queue.Manager(self.MulticastData)
		self.Multicast 			= ILayer
		self.Running 			= True
		self.MyInfo				= None
		self.UserEventsCallback	= None
		self.SecTicker			= 0

		self.Multicast.RegisterEventQueue(self.MulticastIn)
	
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
			if time.time() - int(user["timestamp"]["last_updated"]) > 30:
				#ip 		 = user["sender"]["ip"]
				#port 	 = user["data"]["server"]["socket"]["port"]
				#hash_key = co_security.Hashes().GetHashMd5("{0}_{1}".format(ip,str(port)))
				# User disconnected
				# print("(MulticastData)# Timeout {0}:{1} ({2})".format(ip, port, hash_key))
				del_users.append(key)
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
		self.Multicast.Run()

		while self.Running is True:
			self.SecTicker += 1
			if (self.SecTicker % 25) == 0:
				self.Beacon()
				self.CheckDisconnectedUsers()
			time.sleep(1)
	
	def GetUsers(self):
		return self.Users