import threading
import _thread
import traceback
import time

from core.mks import mks_config
from core import co_queue
from core import co_logger

class NetworkHandler():
	def __init__(self):
		self.MessageQueue = co_queue.Manager(self.MessageQueueHandler)
		self.Hive = None
	
	def MessageQueueHandler(self, msg):
		msg_type = msg["type"]
		msg_data = msg["data"]
		if "new_sock" in msg_type:
			# print(msg_data["sock"].getsockname())
			hash_key = self.Hive.EnhiveSocket(msg_data["sock"], msg_data["ip"], msg_data["port"], "IN", None)
			msg_data["hash"] = hash_key # Add HASH number to instance
			if self.SocketCreatedCallback is not None:
				self.SocketCreatedCallback({
					"event": "new_sock",
					"event_data": msg_data
				})
		elif "new_data" in msg_type:
			sock = msg_data["sock"]
			if sock not in self.SockMap:
				return
			
			sock_info = self.SockMap[sock]
			# Update TS for monitoring
			sock_info["data"]["timestamp"]["last_updated"] = time.time()
			# Append recieved data to the previuose portion
			sock_info["data"]["stream"] += msg_data["data"]

			mks_data 		= sock_info["data"]["stream"]
			mks_data_len 	= len(sock_info["data"]["stream"])

			working = True
			while working is True:
				mkss_index 		= mks_data.find("MKSS".encode())
				mkse_index 		= mks_data.find("MKSE".encode())

				if mkss_index != -1 and mkse_index != -1:
					# Found MKS packet
					data = mks_data[mkss_index+4:mkse_index]
					
					# Raise event for listeners
					if self.SocketDataArrivedCallback is not None:
						self.SocketDataArrivedCallback({
							"event": "new_data",
							"event_data": {
								"sock_info": sock_info,
								"data": data
							}
						})
					
					mks_data = mks_data[mkse_index+4:mks_data_len]
					sock_info["data"]["stream"] = mks_data
				else:
					# Did not found MKS packet
					# co_logger.LOGGER.Log("Networking (SocketEventHandler) NO MAGIC NUMBER IN PACKET.", 1)
					return
		elif "close_sock" in msg_type:
			sock = msg_data
			if sock not in self.SockMap:
				return
			sock_info = self.SockMap[sock]
			ip = sock_info["data"]["ip"]
			port = sock_info["data"]["port"]
			self.Hive.DehiveSocket(ip, port)
			if self.SocketClosedCallback is not None:
				self.SocketClosedCallback({
					"event": "close_sock",
					"event_data": sock_info["data"]
				})
		elif "send" in msg_type:
			hash_key 	= msg_data["hash"]
			data 		= msg_data["data"]
			sock_info 	= self.Hive.OpenConnections[hash_key]
			try:
				data_length		= len(data)
				chunck_size 	= 65536
				num_of_chuncks 	= int(data_length / chunck_size)

				if num_of_chuncks == 0:
					sock_info["data"]["socket"].send(("MKSS"+data+"MKSE").encode())
				else:
					for idx in range(num_of_chuncks):
						if idx == 0:
							sock_info["data"]["socket"].send(("MKSS"+data[idx * chunck_size:(idx + 1) * chunck_size]).encode())
						else:
							sock_info["data"]["socket"].send((data[idx * chunck_size:(idx + 1) * chunck_size]).encode())
						time.sleep(0.1)
					left_over = data_length % chunck_size
					sock_info["data"]["socket"].send((data[data_length-left_over:data_length]+"MKSE").encode())
			except Exception as e:
				co_logger.LOGGER.Log("SocketQueueHandler [SEND] ({}) Exception: {}".format(len(data), str(e)), 1)

	def PushMessage(self, msg):
		self.MessageQueue.QueueItem(msg)