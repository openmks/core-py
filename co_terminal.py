import os

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
			"iface":		self.IFaceHandler
		}

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
		cmd = 'start chrome --window-size={},{} -incognito --app="http://{}:{}"'.format(self.Config.Application["autolaunch"]["width"], self.Config.Application["autolaunch"]["height"],str(self.Config.Application["server"]["address"]["ip"]), str(self.Config.Application["server"]["web"]["port"]))
		objFile = co_file.File()
		objFile.Save("ui.cmd", cmd)
		subprocess.call(["ui.cmd"])
		print("Exit UI session.")
		#self.Exit()

	def AppHandler(self, data):
		import webview
		path = "http://{0}:{1}".format(str(self.Config.Application["server"]["address"]["ip"]), str(self.Config.Application["server"]["web"]["port"]))
		co_logger.LOGGER.Log("({classname})# (AppHandler) Path = {}".format(path, classname=self.ClassName), 1)
		window = webview.create_window(self.ApplicationName, path, width=1600, height=800) # fullscreen=True
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
