import time
import json
import _thread
import socket

from core.mks import mks_config
from core import co_queue
from core import co_security
from core import co_logger

class StaticRoutes():
	def __init__(self, network):
		self.Config				= mks_config.NodeConfig()
		self.Users 				= {}
		self.Network 			= network
		self.Running 			= True
		self.UserEventsCallback	= None
		self.Routes 			= None
	
	def EmitEvent(self, event, info):
		if self.UserEventsCallback is not None:
			self.UserEventsCallback(event, info)
	
	def CheckRoutes(self):
		if self.Routes is None:
			return
		
		for route in self.Routes:
			ip = route["ip"]
			port = route["port"]

			info = self.Network.GetSocketInfoByIpPort(ip, port)
			if info is None:
				# Requested route is not connected
				hash_key = self.Network.Connect(ip, port, None)
				if hash_key is None:
					if "availabale" in route:
						if route["availabale"] is True:
							# Emit event route unavailable
							self.EmitEvent("disconnected", route)
					else:
						pass

					route["availabale"] = False
					route["hash_key"]   = ""
				else:
					#if "availabale" in route:
					#	if route["availabale"] is False:
					#		# Emit event route available
					#		self.EmitEvent("connected", route)
					#else:
					#	# Emit event route available
					#	self.EmitEvent("connected", route)

					route["availabale"] = True
					route["hash_key"]   = hash_key
					self.Network.Disconnect(ip, port)
					self.EmitEvent("connected", route)
			else:
				if "availabale" in route:
					# Check info name
					# co_logger.LOGGER.Log("(StaticRoutes)# [CheckRoutes] Check info name {}:{}".format(ip, port), 1)
					self.EmitEvent("exist", route)
				else:
					co_logger.LOGGER.Log("(StaticRoutes)# [CheckRoutes] Connection taken {}:{}".format(ip, port), 1)
	
	def Run(self):
		_thread.start_new_thread(self.Worker, ())

	def Stop(self):
		self.Running = False

	def Worker(self):
		co_logger.LOGGER.Log("(StaticRoutes)# Start worker", 1)

		status = self.Config.Load()
		if status is False:
			False
		
		self.Routes = self.Config.Application["server"]["static"]["users"]
		self.Running = True
		time.sleep(0.5)
		while self.Running is True:
			self.CheckRoutes()
			time.sleep(5)