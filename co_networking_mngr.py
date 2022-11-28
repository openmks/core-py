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
from core import co_networking_server
	
class Networking(co_definitions.ILayer):
	def __init__(self, handlers):
		co_definitions.ILayer.__init__(self)
		self.Networks = {}

		self.Handlers 							= handlers
		self.Handlers["connect_neighbor"] 		= self.ConnectNeighborHandler
		self.Handlers["disconnect_neighbor"] 	= self.DisconnectNeighborHandler
		self.Handlers["send_data_to_neighbor"] 	= self.SendDataToNeighborHandler

	def BuildNetwork(self, network_name, network_handler):
		try:
			network = co_networking_server.NetworkServer(network_handler)
			network_handler.Hive = network.Hive
			self.Networks[network_name] = network
		except Exception as e:
			co_logger.LOGGER.Log("BuildNetwork <Exception>: {} \n=======\nTrace: {}=======".format(str(e), traceback.format_exc()), 1)
			return None

		return network
	
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

		#try:
		#	hash = self.Connect(ip, port, None)
		#except Exception as e:
		#	return {
		#		"error": str(e),
		#		"hash": hash
		#	}
			
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

		#try:
		#	self.Disconnect(ip, port)
		#except Exception as e:
		#	return {
		#		"error": str(e)
		#	}
			
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

		#try:
		#	status = self.Send(ip, port, data)
		#except Exception as e:
		#	return {
		#		"error": str(e),
		#		"status": status
		#	}
			
		return {
			"error": "",
			"status": status
		}
	