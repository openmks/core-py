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
	
	def GetTable(self, tbl_name):
		if tbl_name in self.DataBase:
			return self.DataBase[tbl_name]
		return None

	def AppendTable(self, name):
		if name not in self.DataBase:
			self.DataBase[name] = []
			return True
		return False
	
	def AppendRowToTable(self, tbl_name, row):
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
	
	def UpdateRow(self, tbl_name, index, row):
		if tbl_name in self.DataBase:
			for item in self.DataBase[tbl_name]:
				if item["index"] == index:
					item["index"] = row
					return True
		return False
	
	def DeleteRow(self, tbl_name, index):
		if tbl_name in self.DataBase:
			del_index = -1
			for idx, item in enumerate(self.DataBase[tbl_name]):
				if item["index"] == index:
					del_index = idx
					break
			
			print("DeleteRow", del_index)
			
			if del_index == -1:
				return False
			else:
				del self.DataBase[tbl_name][del_index]
				return True
		return False
