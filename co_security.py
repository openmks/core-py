import hashlib

class Hashes():
	def __init__(self):
		pass
	
	def GetHashMd5(self, data):
		md5Obj = hashlib.md5(data.encode())
		return md5Obj.hexdigest()