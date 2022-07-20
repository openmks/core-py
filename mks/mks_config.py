import os
import json

from core import co_file
from core import co_security
from core import co_common

class NodeConfig():
	def __init__(self):
		self.MKSEnvPath 	= None # os.path.join(os.environ['HOME'],"mks")
		self.Application 	= None
		self.Terminal 		= None
		self.Logger 		= None
		self.Network 		= None
		self.User 			= None
		self.Hash 			= None
		self.NetworkCards	= co_common.GetIPList()
		self.LocalIPAddress = ""
	
	def ListIface(self):
		return self.NetworkCards
	
	def GetIPAddress(self):
		# Find iface with same UUID as in config file
		for network in self.NetworkCards:
			if network["iface"] in self.Network["iface"]:
				return network["ip"]
		return None

	def Load(self):
		strJson = co_file.File().Load("config.json")
		if (strJson is None or len(strJson) == 0):
			return False
		
		try:
			config = json.loads(strJson)
			if "application" in config:
				self.Application = config["application"]
			if "terminal" in config:
				self.Terminal = config["terminal"]
			if "logger" in config:
				self.Logger = config["logger"]
			if "network" in config:
				self.Network = config["network"]
			if "user" in config:
				self.User = config["user"]

			self.LocalIPAddress = self.GetIPAddress()
			if self.LocalIPAddress is not None:
				self.Application["server"]["address"]["ip"] = self.LocalIPAddress
			else:
				self.LocalIPAddress = "localhost"
			self.Hash = co_security.Hashes().GetHashMd5(json.dumps(self.Application))
		except Exception as e:
			return False
		
		return True
