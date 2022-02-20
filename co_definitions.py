import _thread

class ITask():
	def __init__(self, name):
		self.TaskEnabled 	= False
		self.Running 		= False
		self.Paused 		= False

	def Start(self):
		if self.TaskEnabled is False:
			self.TaskEnabled = True
			_thread.start_new_thread(self.WorkerThread, ())
		
		self.Paused  = False

	def Stop(self):
		if self.Running is True:
			self.Running = False
	
	def Pause(self):
		self.Paused = True
	
	def Resume(self):
		self.Paused = False
	
	def WorkerThread(self):
		self.Running = True
		while self.Running is True:
			if self.Paused is False:
				self.Handler()
		self.TaskEnabled = False

	def Handler(self):
		pass

class ILayer():
	def __init__(self):
		self.FatalError = False
	
	def Run(self):
		pass