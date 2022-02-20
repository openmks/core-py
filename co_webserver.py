#!/usr/bin/python
import os
import _thread
from flask import Flask, render_template, jsonify, Response, request
# from flask_cors import CORS

class EndpointAction(object):
	def __init__(self, page, args):
		self.Page = page + ".html"
		self.DataToJS = args

	def __call__(self, *args):
		print("Broswer Type", request.user_agent.browser)
		print("Broswer Platform", request.user_agent.platform)

		page_path = self.Page
		if "index.html" in self.Page:
			if request.user_agent.platform in ["android"]:
				page_path = os.path.join("index_mobile.html")
			else:
				page_path = os.path.join("index_default.html")
			
		print(page_path)

		return render_template(page_path, data=self.DataToJS), 200, {
			'Cache-Control': 'no-cache, no-store, must-revalidate',
			'Pragma': 'no-cache',
			'Expires': '0',
			'Cache-Control': 'public, max-age=0'
		}

class WebInterface():
	def __init__(self, name, port):
		self.ClassName 	= "WebInterface"
		self.App 		= Flask(name)
		self.Port 		= port
		self.FlaskError	= False

		self.ErrorEventHandler = None

		# self.App.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
		# CORS(self.App)
		# self.Log = logging.getLogger('werkzeug')
		# self.Log.disabled = True
		# self.App.logger.disabled = True

	def WebInterfaceWorker_Thread(self):
		print ("({classname})# Starting local webface on port ({port}) ...".format(classname=self.ClassName, port=str(self.Port)))
		try:
			self.App.run(host='0.0.0.0', port=self.Port)
		except Exception as e:
			print("WebInterfaceWorker_Thread Exception: {0}".format(str(e)))
			self.FlaskError = True
			if self.ErrorEventHandler is not None:
				self.ErrorEventHandler()

	def Run(self):
		_thread.start_new_thread(self.WebInterfaceWorker_Thread, ())

	def AddEndpoint(self, endpoint=None, endpoint_name=None, handler=None, args=None, method=['GET']):
		if handler is None:
			self.App.add_url_rule(endpoint, endpoint_name, EndpointAction(endpoint_name, args))
		else:
			self.App.add_url_rule(endpoint, endpoint_name, handler, methods=method)
