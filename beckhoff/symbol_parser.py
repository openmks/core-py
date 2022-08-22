class SymbolParser():
	def __init__(self):
		self.ADS_DATA_TYPES = [
			"BOOL",
			"BYTE",
			"DINT",
			"DWORD",
			"INT",
			"LINT",
			"LREAL",
			"REAL",
			"SINT",
			"STRING",
			"WSTRING",
			"ULINT",
			"UDINT",
			"UINT",
			"USINT",
			"WORD",
			"enum"
		]

		self.ADS_CONTAINED_DATA_TYPES = [
			"STRING",
			"ARRAY"
		]

		self.WHITELIST = []

		self.ADS_BLACK_LIST 	= []
		self.ParsedTMCData		= None
		self.ADSSymbols			= {}
		self.LayerDepth 		= 20

		self.DataTypesHashMap 	= {}
	
	def ParseDataTypes(self):
		tmc_types = self.ParsedTMCData["DataTypes"]
		print("[#] Build data types hash map.")
		for name in tmc_types:
			tmc_type = tmc_types[name]
			members  = []
			for subitem in tmc_type["members"]:
				members.append({
					"name": subitem["name"],
					"type": subitem["type"]
				})
			
			self.DataTypesHashMap[name] = members
	
	def BuildLayer(self, data, is_nested, layer):
		if layer == 0:
			return data
		
		this_layer_data = {}
		for idx, name in enumerate(data):
			type = data[name]
			this_layer_data[name] = type
			if type not in self.ADS_DATA_TYPES and type not in self.ADS_BLACK_LIST:
				if type not in self.DataTypesHashMap:
					self.ADS_BLACK_LIST.append(type)
				elif "FB_" in type:
					pass
				else:
					members = self.DataTypesHashMap[type]
					if len(members) == 0:
						self.ADS_BLACK_LIST.append(type)
					if len(members) > 0:
						next_layer = {}
						for member in members:
							next_layer[name+"."+member["name"]] = member["type"]
						
						del this_layer_data[name]
						lower_layer_data = self.BuildLayer(next_layer, True, layer-1)
						for name in lower_layer_data:
							this_layer_data[name] = lower_layer_data[name]
			else:
				pass
		
		return this_layer_data
	
	def ParseADSSymbols(self):
		# Find structured items
		print("[#] Parse ADS symbols.")
		data = self.BuildLayer(self.ADSSymbols, False, self.LayerDepth)
		meta_data = {
			"meta": {
				"layer_depth": self.LayerDepth
			},
			"data_types": self.DataTypesHashMap,
			"black_list": self.ADS_BLACK_LIST,
			"symbols_map": data
		}

		return meta_data
	
	def FilterWhiteList(self, name):
		for filter in self.WHITELIST:
			if filter in name:
				return True
		return False
		
	def Parse(self, data, white_list):
		self.WHITELIST 		= white_list
		self.ParsedTMCData 	= data

		for symbol in self.ParsedTMCData["DataArea"]:
			# Filter first layer
			if self.FilterWhiteList(symbol["name"]) is True:
				self.ADSSymbols[symbol["name"]] = symbol["type"]

		self.ParseDataTypes()
		return self.ParseADSSymbols()