import json

from core import co_file

class DB():
	def __init__(self):
		self.DataBase 		= None
		self.Location 		= None
		self.DataBaseLoaded = False
	
	def Load(self, location):
		self.Location = location

		try:
			str_json = co_file.File().Load(location)
			if (str_json is None or len(str_json) == 0):
				self.DataBaseLoaded = False
				return False
			self.DataBase = json.loads(str_json)
		except:
			self.DataBaseLoaded = False
		
		self.DataBaseLoaded = True
		return self.DataBaseLoaded
	
	def Save(self):
		if self.DataBaseLoaded is True:
			try:
				co_file.File().SaveJSON(self.Location, self.DataBase)
			except:
				return False
			
			return True
		
		return False
	
	def CreateDatabase(self, name):
		self.DataBase = {}
		if self.Location is None:
			self.Location = name
		self.DataBaseLoaded = True
	
	def GetTable(self, tbl_name):
		try:
			if tbl_name in self.DataBase:
				return self.DataBase[tbl_name]
		except:
			pass
		return None

	def CreateTable(self, name):
		if name not in self.DataBase:
			self.DataBase[name] = []
			return True
		return False
	
	def SelectRow(self, tbl_name, where):
		ret = []
		if tbl_name in self.DataBase:
			for item in self.DataBase[tbl_name]:
				counter = 0
				for key in where:
					if key in item:
						if where[key] == item[key]:
							counter += 1
				if counter == len(where):
					return ret.append(item)
		return []
	
	def InsertRow(self, tbl_name, row):
		if tbl_name in self.DataBase:
			# Find last index
			max_index = 0
			for item in self.DataBase[tbl_name]: 
				if item["index"] > max_index:
					max_index = item["index"]
			
			# last_index = len(self.DataBase[tbl_name]) + 1
			row["index"] = max_index + 1
			self.DataBase[tbl_name].append(row)
			return True
		return False
	
	def UpdateRow(self, tbl_name, where, param, value):
		if tbl_name in self.DataBase:
			for item in self.DataBase[tbl_name]:
				counter = 0
				for key in where:
					if key in item:
						if where[key] == item[key]:
							counter += 1
				if counter == len(where):
					item[param] = value
					return True
		return False
	
	def DeleteRow(self, tbl_name, where):
		if tbl_name in self.DataBase:
			del_index = -1
			for idx, item in enumerate(self.DataBase[tbl_name]):
				counter = 0
				for key in where:
					if key in item:
						if where[key] == item[key]:
							counter += 1
				# print(counter, len(where))
				if counter == len(where):
					del_index = idx
					break
			
			if del_index == -1:
				return False
			else:
				del self.DataBase[tbl_name][del_index]
				return True
		return False
	
	def GetItemIndex(self, tbl_name, where):
		if tbl_name in self.DataBase:
			for item in self.DataBase[tbl_name]:
				counter = 0
				for key in where:
					if key in item:
						if where[key] == item[key]:
							counter += 1
				if counter == len(where):
					return int(item["index"])
		return 0
	
	def UpdateRowByIndex(self, tbl_name, index, param, value):
		if tbl_name in self.DataBase:
			for item in self.DataBase[tbl_name]:
				if item["index"] == index:
					item[param] = value
					return True
		return False
	
	def DeleteRowByIndex(self, tbl_name, index):
		if tbl_name in self.DataBase:
			del_index = -1
			for idx, item in enumerate(self.DataBase[tbl_name]):
				if item["index"] == index:
					del_index = idx
					break
			
			if del_index == -1:
				return False
			else:
				del self.DataBase[tbl_name][del_index]
				return True
		return False
