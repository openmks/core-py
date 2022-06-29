#!/usr/bin/python
import os
import sys
import json

class File ():
	def __init__(self):
		self.Name = "Save/Load from file"
	
	def Create(self, filepath):
		file = open(filepath, "w")
		file.close()

	def Save (self, filename, data):
		file = open(filename, "w")
		file.write(data)
		file.close()

	def SaveArray (self, filename, data):
		file = open(filename, "wb")
		array = bytearray(data)
		file.write(array)
		file.close()
	
	def AppendArray (self, filename, data):
		print(filename)
		file = open(filename, "a")
		array = bytearray(data)
		file.write(array)
		file.close()

	def Append (self, filename, data):
		file = open(filename, "a")
		file.write(data)
		file.close()

	def Load(self, filename):
		if os.path.isfile(filename) is True:
			file = open(filename, "r")
			data = file.read()
			file.close()
			return data
		return ""
	
	def LoadJson(self, filename):
		if os.path.isfile(filename) is True:
			file = open(filename, "r")
			data = file.read()
			file.close()
			return json.loads(data)
		return None
	
	def LoadBytes(self, filename):
		if os.path.isfile(filename) is True:
			file = open(filename, "rb")
			data = file.read()
			file.close()
			return data
		return None
	
	def WriteBytes(self, filename, data):
		file = open(filename, "wb")
		file.write(data)
		file.close()
	
	def CreateFloder(self, folder_path):
		try:
			if os.path.exists(folder_path):
				return True
			else:
				os.mkdir(folder_path)
		except:
			return False

		return True
	
	def DeleteFile(self, file_path):
		try:
			if os.path.exists(file_path):
				os.remove(file_path)
			else:
				return False
		except:
			return False

		return True
	
	def DeleteFolder(self, dir_pah):
		try:
			if os.path.exists(dir_pah):
				os.rmdir(dir_pah)
			else:
				return False
		except:
			return False

		return True
	
	def GetFileSize(self, path):
		in_bytes = os.path.getsize(path)

		return in_bytes
	
	def SaveJSON(self, filename, data):
		db_file = open(filename, "w")
		json.dump(data, db_file, indent=2)
		db_file.close()
	
	def AppendJSON(self, filename, data):
		db_file = open(filename, "a")
		json.dump(data, db_file, indent=2)
		db_file.close()
	
	def ListFilesInFolder(self, path):
		onlyfiles = []
		try:
			onlyfiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
		except Exception as e:
			print("[File] (ListFilesInFolder) Exception {}".format(str(e)))
		
		return onlyfiles
	
	def ListFoldersInPath(self, path):
		onlyfiles = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
		return onlyfiles
	
	def ListAllInFolder(self, path):
		onlyfiles = [f for f in os.listdir(path)]
		return onlyfiles