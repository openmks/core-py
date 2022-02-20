import os
import struct
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring

class StructParser:
	def __init__(self, schema):
		self.Schema = schema
	
	def ConvertListToInteger(self, buffer):
		buffer_size = len(buffer)
		if buffer_size > 4:
			return 0
		
		value = 0
		for index in range(buffer_size):
			value |= buffer[index] << (index * 8)
			# value |= buffer[index] << ( ((buffer_size - 1) - index) * 8)
		
		return value
	
	def ParseXML(self, buffer):
		index = 0
		with open(self.Schema, 'r') as xml_file:
			tree = ET.parse(xml_file)
			for elem in tree.iter():
				if elem.get('item') == "value":
					size = int(elem.get('size'))
					# print(elem.tag)
					if elem.get('type') == "int":
						if size == 1:
							elem.text = str(self.ConvertListToInteger(buffer[index:index+1]))
						elif size == 2:
							elem.text = str(self.ConvertListToInteger(buffer[index:index+2]))
						elif size == 4:
							elem.text = str(self.ConvertListToInteger(buffer[index:index+4]))
	
						index += size
					elif elem.get('type') == "string":
						try:
							str_data = ""
							for item in buffer[index:index+size]:
								if item > 0x20 and item < 0x7f:
									str_data += chr(item)
							elem.text = str_data
						except Exception as e:
							print("[ParseBINtoXML] - ERROR - {0}".format(e))
						index += size
				elif elem.get('item') == "array":
					pass	
				else:
					pass
		
		return tostring(tree.getroot())