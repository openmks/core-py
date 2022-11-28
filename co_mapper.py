class DictionaryMapper():
	def __init__(self):
		self.Map = {}

	def Add(self, key, value):
		self.Map[key] = value

	def Del(self, key):
		if key in self.Map:
			del self.Map[key]
	
	def Exist(self, key):
		return key in self.Map

	def Clean(self, key, value):
		self.Map.clear()
