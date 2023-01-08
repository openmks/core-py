import psutil
import win32gui
import win32process
import ctypes
import socket
import subprocess

from core import co_logger
from core import co_file
from core.mks import mks_config

#EnumWindows 		= ctypes.windll.user32.EnumWindows
#EnumWindowsProc 	= ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
#IsWindowVisible 	= ctypes.windll.user32.IsWindowVisible

class INode():
	def __init__(self, name):
		self.NodeName 	= name
		self.ValidToRun = True
		if self.CheckPort() is False:
			self.ValidToRun = False
			self.StartChrome()

	def StartChrome(self):
		config = mks_config.NodeConfig()
		if config.Load() is False:
			return False
		
		cmd = 'start chrome -incognito http://{}:{}'.format(str(config.Application["server"]["address"]["ip"]), str(config.Application["server"]["web"]["port"]))
		objFile = co_file.File()
		objFile.Save("ui.cmd", cmd)
		subprocess.call(["ui.cmd"])
		return True
	
	def CheckPort(self):
		config = mks_config.NodeConfig()
		if config.Load() is False:
			return False
		
		try:
			port = config.Application["server"]["web"]["port"]
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.bind(('', port))
			sock.close()
			return True
		except:
			return False

	def CheckInstance(self):
		for proc in psutil.process_iter():
			try:
				# Get process name & pid from process object.
				if proc.name() in ["python.exe","cmd.exe"]:
					hwndl = self.get_hwnds_for_pid(proc.pid)
					print(hwndl, proc.pid, proc.name())
					if len(hwndl) > 0:
						co_logger.LOGGER.Log("[CheckInstance] {}".format(self.getWindowTitleByHandle(hwndl[0])), 1)
			except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
				pass
	
	def get_hwnds_for_pid(self, pid):
		def callback(hwnd, hwnds):
			#if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
			_, found_pid = win32process.GetWindowThreadProcessId(hwnd)

			if found_pid == pid:
				hwnds.append(hwnd)
			return True
		hwnds = []
		win32gui.EnumWindows(callback, hwnds)
		return hwnds 
	
	def getWindowTitleByHandle(self, hwnd):
		length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
		buff = ctypes.create_unicode_buffer(length + 1)
		ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)

		return buff.value