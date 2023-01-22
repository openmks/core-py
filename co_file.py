#!/usr/bin/python
import os
import sys
import json
import time
import pathlib

class File ():
	def __init__(self):
		self.Name = "Save/Load from file"
	
	def Create(self, filepath):
		file = open(filepath, "w")
		file.close()

	def Save (self, filename, data):
		file = open(filename, "w", encoding="utf8")
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
		try:
			if os.path.isfile(filename) is True:
				file = open(filename, "r", encoding="utf8")
				data = file.read()
				file.close()
				return data
		except Exception as e:
			print("[File] (Load) {} Exception {}".format(filename, str(e)))

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
	
	def PathExists(self, folder_path):
		if os.path.exists(folder_path):
			return True

		return False
	
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
	
	def delete_folder(self, pth):
		for sub in pth.iterdir():
			if sub.is_dir() :
				self.delete_folder(sub)
			else :
				sub.unlink()
		pth.rmdir()
	
	def DeleteFolder(self, dir_path):
		try:
			if os.path.exists(dir_path):
				# os.rmdir(dir_path)
				self.delete_folder(pathlib.Path(dir_path))
			else:
				return False
		except Exception as e:
			return False

		return True
	
	def GetFileDate(self, path):
		ti_c = os.path.getctime(path)
		ti_m = os.path.getmtime(path)
		
		# Converting the time in seconds to a timestamp
		c_ti = time.ctime(ti_c)
		m_ti = time.ctime(ti_m)

		return {
			"created": c_ti,
			"modified": m_ti
		}
	
	def GetFileSize(self, path):
		in_bytes = 0.0
		if os.path.exists(path):
			in_bytes = os.path.getsize(path)

		return in_bytes
	
	def SaveJSON(self, file_path, data):
		db_file = open(file_path, "w")
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