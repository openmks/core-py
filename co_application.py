import os
import json
import time
import _thread
from collections import OrderedDict
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource

from core import co_webserver
from core import co_definitions
from core import co_file
from core.mks import mks_config

class WebsocketLayer():
	def __init__(self):
		self.ClassName				= "WebsocketLayer"
		self.ApplicationSockets		= {}
		self.ServerRunning			= False
		# Events
		self.OnWSConnected			= None
		self.OnDataArrivedEvent		= None
		self.OnWSDisconnected		= None
		self.OnSessionsEmpty		= None
		self.Port					= 0
	
	def RegisterCallbacks(self, connected, data, disconnect, empty):
		print ("({classname})# (RegisterCallbacks)".format(classname=self.ClassName))
		self.OnWSConnected		= connected
		self.OnDataArrivedEvent = data
		self.OnWSDisconnected	= disconnect
		self.OnSessionsEmpty	= empty

	def SetPort(self, port):
		self.Port = port
	
	def AppendSocket(self, ws_id, ws):
		print ("({classname})# Append ({0})".format(ws_id, classname=self.ClassName))
		self.ApplicationSockets[ws_id] = ws
		if self.OnWSConnected is not None:
			self.OnWSConnected(ws_id)
	
	def RemoveSocket(self, ws_id):
		print ("({classname})# Remove ({0})".format(ws_id, classname=self.ClassName))
		del self.ApplicationSockets[ws_id]
		if self.OnWSDisconnected is not None:
			self.OnWSDisconnected(ws_id)
		if len(self.ApplicationSockets) == 0:
			if self.OnSessionsEmpty is not None:
				self.OnSessionsEmpty()
	
	def WSDataArrived(self, ws, data):
		packet = json.loads(data)
		# print ("({classname})# Data {0}".format(id(ws),classname=self.ClassName))
		if self.OnDataArrivedEvent is not None:
			self.OnDataArrivedEvent(ws, packet)
	
	def Send(self, ws_id, data):
		if ws_id in self.ApplicationSockets:
			try:
				self.ApplicationSockets[ws_id].send(json.dumps(data))
			except Exception as e:
				print ("({classname})# [ERROR] Send {0}".format(str(e), classname=self.ClassName))
		else:
			print ("({classname})# [ERROR] This socket ({0}) does not exist. (Might be closed)".format(ws_id, classname=self.ClassName))
	
	def EmitEvent(self, data):
		for key in self.ApplicationSockets:
			self.ApplicationSockets[key].send(json.dumps(data))
	
	def IsServerRunnig(self):
		return self.ServerRunning

	def Worker(self):
		try:
			server = WebSocketServer(('0.0.0.0', self.Port), Resource(OrderedDict([('/', WSApplication)])))

			self.ServerRunning = True
			print ("({classname})# Staring local WS server ... {0}".format(self.Port, classname=self.ClassName))
			server.serve_forever()
		except Exception as e:
			print ("({classname})# [ERROR] Stoping local WS server ... {0}".format(str(e), classname=self.ClassName))
			self.ServerRunning = False
	
	def RunServer(self):
		if self.ServerRunning is False:
			_thread.start_new_thread(self.Worker, ())

WSManager = WebsocketLayer()

class WSApplication(WebSocketApplication):
	def __init__(self, *args, **kwargs):
		self.ClassName = "WSApplication"
		super(WSApplication, self).__init__(*args, **kwargs)
	
	def on_open(self):
		print ("({classname})# CONNECTION OPENED".format(classname=self.ClassName))
		WSManager.AppendSocket(id(self.ws), self.ws)

	def on_message(self, message):
		# print ("({classname})# MESSAGE RECIEVED {0} {1}".format(id(self.ws),message,classname=self.ClassName))
		if message is not None:
			WSManager.WSDataArrived(self.ws, message)
		else:
			print ("({classname})# [ERROR] Message is not valid".format(classname=self.ClassName))

	def on_close(self, reason):
		print ("({classname})# CONNECTION CLOSED".format(classname=self.ClassName))
		WSManager.RemoveSocket(id(self.ws))

class ApplicationLayer(co_definitions.ILayer):
	def __init__(self):
		co_definitions.ILayer.__init__(self)
		self.WSHandlers = {
			'get_file': 	self.GetFileRequestHandler,
			'get_resource': self.GetResourceRequestHandler,
		}
		self.Ip 	    = None
		self.Port 	    = None
		# TODO - Not all nodes hav HW
		# self.HW 		= None
		self.Config 	= mks_config.NodeConfig()
		self.Web		= None
	
	def SetIp(self, ip):
		self.Ip = ip
	
	def SetPort(self, port):
		self.Port = port
	
	def Worker(self):
		pass
	
	def Start(self):
		_thread.start_new_thread(self.Worker, ())
	
	def Run(self):
		status = self.Config.Load()
		if status is False:
			print("ERROR - Wrong configuration format")
			return False
		
		print("Local IP {0}".format(self.Config.LocalIPAddress))
		ip_addr = str(self.Config.Application["server"]["address"]["ip"])
		if self.Config.Application["server"]["address"]["use_local_ip"] is True:
			ip_addr = str(self.Config.LocalIPAddress)
		# Data for the pages.
		web_data = {
			'ip': ip_addr,
			'port': str(self.Config.Application["server"]["web_socket"]["port"])
		}
		data = json.dumps(web_data)
		self.Web = co_webserver.WebInterface("Context", self.Config.Application["server"]["web"]["port"])
		self.Web.ErrorEventHandler = self.WebErrorEvent
		self.Web.AddEndpoint("/", "index", None, data)
		self.Web.Run()

		self.Start()

		time.sleep(0.5)
		WSManager.RegisterCallbacks(self.WSConnectedHandler, self.WSDataArrivedHandler, self.WSDisconnectedHandler, self.WSSessionsEmpty)
		WSManager.SetPort(self.Config.Application["server"]["web_socket"]["port"])
		WSManager.RunServer()

		return True
	
	def WebErrorEvent(self):
		pass

	def GetResourceRequestHandler(self, sock, packet):
		print("GetResourceRequestHandler {0}".format(packet))
		objFile = co_file.File()

		path	= os.path.join(".", "static", "js", "application", "resource", packet["payload"]["file_path"])
		content = objFile.Load(path)
		
		return {
			'file_path': packet["payload"]["file_path"],
			'content': content.encode("utf-8").hex()
		}
	
	def GetFileRequestHandler(self, sock, packet):
		print("GetFileRequestHandler {0}".format(packet))
		objFile = co_file.File()

		path	= os.path.join(".", "static", packet["payload"]["file_path"])
		content = objFile.Load(path)
		
		return {
			'file_path': packet["payload"]["file_path"],
			'content': content.encode("utf-8").hex()
		}
	
	def WSConnectedHandler(self, ws_id):
		pass

	def WSDataArrivedHandler(self, ws, packet):
		try:
			command = packet["header"]["command"]
			if self.WSHandlers is not None:
				if command in self.WSHandlers.keys():
					message = self.WSHandlers[command](ws, packet)
					if message == "" or message is None:
						return
					packet["payload"] = message
					WSManager.Send(id(ws), packet)
		except Exception as e:
			print("WSDataArrivedHandler Exception: {0}".format(str(e)))

	def WSDisconnectedHandler(self, ws_id):
		pass

	def WSSessionsEmpty(self):
		pass

	# def HWEventHandler(self, event, data):
	#	self.EmitEvent({
	#		'event': event,
	#		'data': data
	#	})

	# def RegisterHardware(self, hw_layer):
	#	self.HW = hw_layer
	#	self.HW.EventCallback = self.HWEventHandler

	def AsyncEvent(self, event_name, data):
		self.EmitEvent({
			'event': event_name,
			'data': data
		})

	def EmitEvent(self, payload):
		packet = {
			'header': {
				'command': 'event',
				'timestamp': str(int(time.time())),
				'identifier': -1
			},
			'payload': payload
		}
		WSManager.EmitEvent(packet)
