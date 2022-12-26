import pyads
import time
import _thread

class EmuADS():
	__slots__ = ('AMSNetId', 'Symbols', 'IsConnected', 'Counter', 'PrevTs', 'CurrTs')
	def __init__(self):
		self.AMSNetId   	= "Simulated"
		self.Symbols		= [{
			"name": "tbl_bla",
			"type": "tbl_type",
			"comment": "emulated",
			"index_group": {
				"access": "R/W"
			}
		}]
		self.IsConnected	= False
		self.Counter 		= 0
		self.PrevTs 		= time.time_ns()
		self.CurrTs 		= time.time_ns()
	
	def Connect(self, ams_net_id):
		self.IsConnected = True
		self.AMSNetId 	 = ams_net_id

		# Start thread
		_thread.start_new_thread(self.Worker, ())

		return True
	
	def Status(self):
		state 	= {}
		status 	= True
		
		return status, state
	
	def Disconnect(self):
		self.IsConnected = False
		self.AMSNetId	 = None
	
	def ReadSymbol(self, name):
		return {"value": "data"}
	
	def WriteSymbol(self, name, value):
		pass
	
	def ReadStructuredSymbol(self, name):
		pass

	def GetValuesFromNameListBurst(self, names):
		symbols = {}
		for idx, symbol in enumerate(names):
			symbols[symbol] = (self.Counter % 10) * (idx + 1)
		# print("R: {} {}".format(self.Counter, (self.CurrTs-self.PrevTs)/1000000.0))
			
		return symbols

	def GetValuesFromNameList(self, names):
		values = {"name": "value"}
		
		return values
	
	def GetAllSymbolsInfo(self):		
		return self.Symbols

	def GetAvailableSymbols(self):
		symbols = []
		for symbol in self.Symbols:
			data = {}
			data[symbol["name"]] = self.Counter
			symbols.append(data)
			
		return symbols
	
	def Worker(self):
		while self.IsConnected is True:
			try:
				self.PrevTs 	= self.CurrTs
				self.CurrTs 	= time.time_ns()

				self.Counter += 1
				time.sleep(0.001)
			except Exception as e:
				pass
	
	def CheckSymbol(self, symbol):
		return True

class ADS():
	__slots__ = ('PLC', 'AMSNetId', 'Symbols', 'IndexGroup', 'IsConnected')
	def __init__(self):
		self.PLC        	= None
		self.AMSNetId   	= None
		self.Symbols		= None
		self.IsConnected	= False

		self.IndexGroup = {
			0x00004020: {
				"access": "R/W"
			},
			0x00004021: {
				"access": "R/W"
			},
			0x00004025: {
				"access": "R"
			},
			0x00004030: {
				"access": "R/W"
			},
			0x00004035: {
				"access": "R"
			},
			0x00004040: {
				"access": "R/W"
			},
			0x00004045: {
				"access": "R"
			},
			0x0000F003: {
				"access": "R&W"
			},
			0x0000F005: {
				"access": "R/W"
			},
			0x0000F006: {
				"access": "W"
			},
			0x0000F020: {
				"access": "R/W"
			},
			0x0000F021: {
				"access": "R/W"
			},
			0x0000F025: {
				"access": "R"
			},
			0x0000F030: {
				"access": "R/W"
			},
			0x0000F031: {
				"access": "R/W"
			},
			0x0000F035: {
				"access": "R"
			},
			0x0000F080: {
				"access": "R&W"
			},
			0x0000F081: {
				"access": "R&W"
			},
			0x0000F082: {
				"access": "R&W"
			}
		}
	
	def AddRoute(self, ams_net_id, my_ip, target_ip, target_username, target_password, rout_name):
		pyads.add_route_to_plc(
			ams_net_id, my_ip, target_ip, target_username, target_password,
			route_name=rout_name
		)
	
	def RemoveRoute(self, ams_net_id):
		pyads.delete_route(ams_net_id)

	def Connect(self, ams_net_id):
		# print("<ADS> Trying to connect {} ...".format(ams_net_id))
		try:
			self.PLC = pyads.Connection(ams_net_id, pyads.PORT_TC3PLC1)
			self.PLC.open()

			# Get status of this connection
			status, state = self.Status()
			self.AMSNetId = ams_net_id

			# print("<ADS> Trying to connect {} ... Status {}".format(ams_net_id, state))
			return status			
		except Exception as e:
			print("<ADS> Connection failed {} ... {}".format(ams_net_id, str(e)))
			return False
	
	def Status(self):
		# print("<ADS> Status {} ...".format(self.AMSNetId))
		state 	= None
		status 	= True
		try:
			state = self.PLC.read_state()
			# print("<ADS> Status {} ... {}".format(self.AMSNetId, state))
		except:
			status = False
		
		self.IsConnected = status
		return status, state
	
	def Disconnect(self):
		# print("<ADS> Disconnect {} ...".format(self.AMSNetId))
		self.PLC.close()
		self.IsConnected = False
		self.AMSNetId	 = None
	
	def ReadSymbol(self, name):
		value = None
		try:
			value = self.PLC.read_by_name(name)
		except:
			pass

		return value
	
	def CheckSymbol(self, symbol):
		value = self.ReadSymbol(symbol)

		if value is None:
			return False
		
		return True
	
	def WriteSymbol(self, name, value):
		self.PLC.write_by_name(name, value)
	
	def ReadStructuredSymbol(self, name):
		pass

	def GetValuesFromNameListBurst(self, names):
		return self.PLC.read_list_by_name(names)

	def GetValuesFromNameList(self, names):
		values = {}

		for name in names:
			value = self.PLC.read_by_name(name)
			values[name] = value
		
		return values
	
	def GetAllSymbolsInfo(self):
		if self.Symbols is None:
			self.Symbols = self.PLC.get_all_symbols()
		
		symbols = []
		for symbol in self.Symbols:
			index_group = None
			if symbol.index_group in self.IndexGroup:
				index_group = self.IndexGroup[symbol.index_group]

			symbols.append({
				"name": symbol.name,
				"type": symbol.symbol_type,
				"comment": symbol.comment,
				"index_group": index_group
			})
		
		return symbols

	def GetAvailableSymbols(self):
		self.Symbols = self.PLC.get_all_symbols()

		symbols = []
		for symbol in self.Symbols:
			value = None
			try:
				value = symbol.read()
			except:
				# Structure read
				pass
		
			index_group = None
			if symbol.index_group in self.IndexGroup:
				index_group = self.IndexGroup[symbol.index_group]
				
			symbols.append({
				"name": symbol.name,
				"type": symbol.symbol_type,
				"value": value,
				"comment": symbol.comment,
				"index_group": index_group
			})
			
		return symbols
