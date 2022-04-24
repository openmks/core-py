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
		self.Hash 			= None
		self.NetworkCards	= co_common.GetIPList()
		self.LocalIPAddress = ""
	
	def GetIPAddress(self):
		for network in self.NetworkCards:
			if network["iface"] in self.Network["iface"]:
				return network["ip"]

	def Load(self):
		strJson = co_file.File().Load("config.json")
		if (strJson is None or len(strJson) == 0):
			return False
		
		try:
			config = json.loads(strJson)
			self.Application = config["application"]
			self.Terminal 	 = config["terminal"]
			self.Logger 	 = config["logger"]
			self.Network	 = config["network"]

			self.LocalIPAddress = self.GetIPAddress()
			if self.LocalIPAddress is not None:
				self.Application["server"]["address"]["ip"] = self.LocalIPAddress
			self.Hash = co_security.Hashes().GetHashMd5(json.dumps(self.Application))
		except Exception as e:
			return False
		
		return True
