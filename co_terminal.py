import os
import json

from core import co_definitions
from core import co_file
from core.mks import mks_config
from core import co_logger

import subprocess

class TerminalLayer(co_definitions.ILayer):
	def __init__(self):
		co_definitions.ILayer.__init__(self)
		self.ClassName			= "TerminalLayer"
		self.ApplicationName 	= "Application"
		self.Application    	= None
		self.ProcessRunning 	= True
		self.Handlers 			= None
		self.Config 			= mks_config.NodeConfig()
		self.Handlers       	= {
			"help":         self.HelpHandler,
			"app":			self.AppHandler,
			"web":			self.WebHandler,
			"exit":			self.ExitHandler,
			"whoami":		self.WhoAmIHandler,
			"iface":		self.IFaceHandler,
			"connlist":		self.ConnectionListHandler,
			"loadcfg":		self.LoadConfigHandler,
			"printcfg": 	self.PrintConfigHandler,
			"version": 		self.VersionHandler
		}

	def VersionHandler(self, data):
		print("Application: {}\nMKS Framwork: {}".format(self.Config.Root["version"], self.Config.Root["mks_ver"]))
	
	def PrintConfigHandler(self, data):
		if self.Config is not None:
			print("Application:\n{}".format(json.dumps(self.Config.Application, indent=2)))
			print("Terminal:\n{}".format(json.dumps(self.Config.Terminal, indent=2)))
			print("Logger:\n{}".format(json.dumps(self.Config.Logger, indent=2)))
			print("Network:\n{}".format(json.dumps(self.Config.Network, indent=2)))
			print("User:\n{}".format(json.dumps(self.Config.User, indent=2)))
	
	def LoadConfigHandler(self, data):
		self.Config.Load()
		if self.Application is not None:
			self.Application.Config.Load()
	
	def ConnectionListHandler(self, data):
		if self.Application is not None:
			print("Local Opened Sockets:\n=====================")
			for idx, conn in enumerate(self.Application.Network.GetConnectionList()):
				print("{}. {}".format(idx+1, conn))
			
			ws_sessions = self.Application.GetSessions()
			print("Web Opened Sockets:\n===================")
			for idx, key in enumerate(ws_sessions):
				'''
					{
						'GATEWAY_INTERFACE': 'CGI/1.1', 
						'SERVER_SOFTWARE': 'gevent/20.0 Python/3.9', 
						'SCRIPT_NAME': '', 'wsgi.version': (1, 0), 
						'wsgi.multithread': False, 
						'wsgi.multiprocess': False, 
						'wsgi.run_once': False, 
						'wsgi.url_scheme': 'http', 
						'wsgi.errors': <_io.TextIOWrapper name='<stderr>' mode='w' encoding='utf-8'>, 
						'SERVER_NAME': 'KIVEISHA2.auth.hpicorp.net', 
						'SERVER_PORT': '1945', 
						'REQUEST_METHOD': 'GET', 
						'PATH_INFO': '/', 
						'QUERY_STRING': '', 
						'SERVER_PROTOCOL': 'HTTP/1.1', 
						'REMOTE_ADDR': '10.0.0.3', 
						'REMOTE_PORT': '61055', 
						'HTTP_HOST': '10.0.0.2:1945', 
						'HTTP_CONNECTION': 'Upgrade', 
						'HTTP_PRAGMA': 'no-cache', 
						'HTTP_CACHE_CONTROL': 'no-cache', 
						'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36', 
						'HTTP_UPGRADE': 'websocket', 
						'HTTP_ORIGIN': 'http://10.0.0.2:2001', 
						'HTTP_SEC_WEBSOCKET_VERSION': '13', 
						'HTTP_ACCEPT_ENCODING': 'gzip, deflate', 
						'HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.9', 
						'HTTP_SEC_WEBSOCKET_KEY': '4XuC8uoxun5gWLdJc5ghGQ==', 
						'HTTP_SEC_WEBSOCKET_EXTENSIONS': 'permessage-deflate; client_max_window_bits', 
						'wsgi.input': <_io.BufferedReader name=1276>, 
						'wsgi.input_terminated': False, 
						'wsgi.websocket_version': '13', 
						'wsgi.websocket': <geventwebsocket.websocket.WebSocket object at 0x000001EA3E0A8D60>}
				'''
				ws_session = ws_sessions[key]
				print("{}. {}".format(idx+1, {
					"REMOTE_ADDR": ws_session.environ.get('REMOTE_ADDR'),
					"REMOTE_PORT": ws_session.environ.get('REMOTE_PORT'),
					"HTTP_HOST": ws_session.environ.get('HTTP_HOST')
				}))

	def IFaceHandler(self, data):
		network_cards = mks_config.NodeConfig().ListIface()
		for idx, network in enumerate(network_cards):
			print("{}. iface: {}\n  IP: {}\n  Mask: {}\n  MAC: {}".format(idx+1, network["iface"], network["ip"], network["mask"], network["mac"]))

	def UpdateApplication(self, data):
		if self.Application is not None:
			self.Application.EmitEvent(data)
	
	def WhoAmIHandler(self, data):
		print(self.Config.Application["name"])
	
	def HelpHandler(self, data):
		for idx, key in enumerate(self.Handlers):
			print("\t{}. {}".format(idx+1, key))

	def ExitHandler(self, data):
		self.Exit()
	
	def WebHandler(self, data):
		# Generate command
		# cmd = 'start chrome --window-size={},{} -incognito --app="http://{}:{}"'.format(self.Config.Application["autolaunch"]["width"], self.Config.Application["autolaunch"]["height"],str(self.Config.Application["server"]["address"]["ip"]), str(self.Config.Application["server"]["web"]["port"]))
		cmd = 'start chrome -incognito http://{}:{}'.format(str(self.Config.Application["server"]["address"]["ip"]), str(self.Config.Application["server"]["web"]["port"]))
		objFile = co_file.File()
		objFile.Save("ui.cmd", cmd)
		subprocess.call(["ui.cmd"])
		print("Exit UI session.")
		#self.Exit()

	def AppHandler(self, data):
		import webview
		path = "http://{0}:{1}".format(str(self.Config.Application["server"]["address"]["ip"]), str(self.Config.Application["server"]["web"]["port"]))
		co_logger.LOGGER.Log("({classname})# (AppHandler) Path = {}".format(path, classname=self.ClassName), 1)
		window = webview.create_window(self.Config.Application["name"], path, width=self.Config.Application["autolaunch"]["width"], height=self.Config.Application["autolaunch"]["height"]) # fullscreen=True
		co_logger.LOGGER.Log("({classname})# (AppHandler) Window = {}".format(window, classname=self.ClassName), 1)
		webview.start()
	
	def AttachApplication(self, app):
		self.Application = app
		self.Application.CloseProcessRequestEvent = self.Exit
	
	def Run(self):
		status = self.Config.Load()
		if status is False:
			print("ERROR - Wrong configuration format")
			return False
		
		if self.Config.Application["autolaunch"]["enabled"] is True:
			if "app" in self.Config.Application["autolaunch"]["type"]:
				self.AppHandler(None)
			elif "web" in self.Config.Application["autolaunch"]["type"]:
				self.WebHandler(None)
		
		while(self.ProcessRunning is True):
			try:
				raw  	= input('> ')
				data 	= raw.split(" ")
				cmd  	= data[0]
				params 	= data[1:]

				if self.Handlers is not None:
					if cmd in self.Handlers:
						self.Handlers[cmd](params)
					else:
						if cmd not in [""]:
							print("unknown command")
			except Exception as e:
				print("Terminal Exception {0}".format(str(e)))
		return True
	
	def Exit(self):
		co_logger.LOGGER.Log("[Terminal] Exit process", 1)
		self.ProcessRunning = False
		os._exit(0)
