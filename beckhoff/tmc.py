import os
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring

class TMC():
	def __init__(self, path):
		self.Path 		= path
		self.NewPath 	= path
	
	def ConvertToXML(self, is_delete):
		try:
			self.NewPath = self.Path.replace(".tmc", ".xml")
			file_exists = os.path.exists(self.NewPath)
			if file_exists is True and is_delete is True:
				os.remove(self.NewPath)
			os.rename(self.Path, self.NewPath)
		except Exception as e:
			pass
	
	def ParseXML(self):
		parsed_data = {}
		tree = None
		try:
			#print(self.NewPath)
			parser = ET.XMLParser()
			tree = ET.parse(self.NewPath, parser)
		except Exception as e:
			print("ParseXML::XMLParser", e)
		
		parsed_data["Properties"] = []
		try:
			for properties in tree.iter("Properties"):
				for property in properties.iter("Property"):
					# Parse object info
					prop_name = property.find("Name")
					prop_value = property.find("Value")
					if prop_name is not None and prop_value is not None:
						parsed_data["Properties"].append({
							"name": prop_name.text,
							"value": prop_value.text
						})
		except Exception as e:
			print("ParseXML::Properties", e)
		
		# Find all DataType nodes
		parsed_data["DataTypes"] = {}
		try:
			for data_type in tree.iter("DataType"):
				# Parse object info
				data_type_name = data_type.find('Name')
				if data_type_name is not None:
					parsed_data["DataTypes"][data_type_name.text] = {
						"name": data_type_name.text,
						"members": []
					}
					for item in data_type.iter():
						if item.tag == "SubItem":
							item_name = item.find("Name")
							item_type = item.find("Type")
							if item_name is not None and item_type is not None:
								parsed_data["DataTypes"][data_type_name.text]["members"].append({
									"item": "SubItem",
									"name": item_name.text,
									"type": item_type.text
								})
						elif item.tag == "EnumInfo":
							item_text = item.find("Text")
							item_enum = item.find("Enum")
							if item_text is not None and item_enum is not None:
								parsed_data["DataTypes"][data_type_name.text]["members"].append({
									"item": "EnumInfo",
									"name": item_text.text,
									"enum": item_enum.text,
									"type": "enum"
								})
		except Exception as e:
			print("ParseXML::DataTypes", e)
		
		parsed_data["DataArea"] = []
		try:
			for data_area in tree.iter("DataArea"):
				# Parse object info
				if data_area is not None:
					data_area_name = data_area.find('Name')
					if data_area_name is not None:
						for item in data_area.iter("Symbol"):
							item_name = item.find("Name")
							item_base_type = item.find("BaseType")
							if item_name is not None and item_enum is not None:
								parsed_data["DataArea"].append({
									"name": item_name.text,
									"type": item_base_type.text,
									"data_area_name": data_area_name.text
								})
		except Exception as e:
			print("ParseXML::DataArea", e)
			
		return parsed_data
	
	def Parse(self, is_delete):
		self.ConvertToXML(is_delete)
		return self.ParseXML()