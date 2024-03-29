import time
import json
import _thread
import socket

from core import co_queue
from core import co_security
from core import co_logger

class Beaconer():
	def __init__(self, ILayer, handlers):
		self.Users 				= {}
		self.MulticastIn		= co_queue.Manager(self.MulticastData)
		self.Multicast 			= ILayer
		self.Running 			= True
		self.MyInfo				= None
		self.UserEventsCallback	= None
		self.SecTicker			= 0

		self.Multicast.RegisterEventQueue(self.MulticastIn)
		self.Handlers 					= handlers
		self.Handlers["get_neighbors"]	= self.GetNeighborsHandler
		self.Handlers["find_neighbors"]	= self.FindNeighborsHandler

		self.MulticastEnbled 	= False
	
	def FindNeighborsHandler(self, sock, packet):
		info = packet["payload"]["info"]
		self.BeaconFind(info)

		return {
			"status": True
		}
	
	def GetNeighborsHandler(self, sock, packet):
		ams_net_id = packet["payload"]["ams_net_id"]
		self.BeaconFind()
		return {
			"users": self.Users
		}
	
	def MulticastData(self, info):
		if self.MulticastEnbled is False:
			co_logger.LOGGER.Log("(Beaconer)# [MulticastData] Milticast is disabled", 1)
			return
		
		hash_key = info["data"]["hash"]
		if hash_key == self.Multicast.Config.Hash:
			return

		if "beacon_find" in info["data"]["cmd"]:
			sonar_info = info["data"]["info"]
			if sonar_info["name"] == self.Multicast.Config.Application["name"]:
				self.Beacon()
			else:
				# Classification
				pass
		
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
	
	def ForceDisconnetedusersCheck(self):
		if self.MulticastEnbled is False:
			co_logger.LOGGER.Log("(Beaconer)# [ForceDisconnetedusersCheck] Milticast is disabled", 1)
			return
		
		del_users = []
		for key in self.Users:
			user = self.Users[key]
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				resp = sock.connect((user["sender"]["ip"], user["data"]["server"]["socket"]["port"]))
			except:
				del_users.append(key)
		
		for key in del_users:
			if self.UserEventsCallback is not None:
				self.UserEventsCallback("del", self.Users[key])
			del self.Users[key]
	
	def CheckDisconnectedUsers(self):
		del_users = []
		for key in self.Users:
			user = self.Users[key]
			if time.time() - int(user["timestamp"]["last_updated"]) > 30:
				del_users.append(key)
		for key in del_users:
			if self.UserEventsCallback is not None:
				self.UserEventsCallback("del", self.Users[key])
			del self.Users[key]
	
	def Beacon(self):
		multicast_msg 			= self.Multicast.Config.Application
		multicast_msg["hash"] 	= self.Multicast.Config.Hash
		multicast_msg["cmd"] 	= "beacon"
		multicast_msg["ver"] 	= 1.0
		self.Multicast.Send(json.dumps(multicast_msg))
	
	def BeaconFind(self, info):
		if self.MulticastEnbled is False:
			co_logger.LOGGER.Log("(Beaconer)# [BeaconFind] Milticast is disabled", 1)
			return
		
		multicast_msg = self.Multicast.Config.Application
		multicast_msg["cmd"]  = "beacon_find",
		multicast_msg["ver"]  = 1.0,
		multicast_msg["hash"] = self.Multicast.Config.Hash
		multicast_msg["info"] = {
			"name": info["name"],
			"identification": {
				"class": {
					"category": info["category"],
					"group": info["group"],
					"type": info["type"]
				}
			}
		}
		
		self.Multicast.Send(json.dumps(multicast_msg))
	
	def Run(self):
		_thread.start_new_thread(self.Worker, ())

	def Stop(self):
		self.Running = False
		self.Multicast.Stop()

	def Worker(self):
		self.MulticastEnbled = self.Multicast.Config.Application["server"]["broadcast"]["enabled"]

		if self.MulticastEnbled is False:
			co_logger.LOGGER.Log("(Beaconer)# Milticast is disabled", 1)
			return
		
		self.Running = True
		
		co_logger.LOGGER.Log("(Beaconer)# Start worker", 1)
		self.MulticastIn.Start()
		self.Multicast.Run()

		time.sleep(0.5)
		self.Beacon()
		while self.Running is True:
			self.SecTicker += 1
			if (self.SecTicker % 20) == 0:
				self.Beacon()
				self.CheckDisconnectedUsers()
			time.sleep(1)
	
	def GetUsers(self):
		return self.Users