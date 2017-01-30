#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import unicode_literals


import sys
import traceback

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import GObject as gobject
from gi.repository import GLib as glib

import base64
import binascii
import hashlib

import sleekxmpp


class Server(sleekxmpp.ClientXMPP):
	def __init__(self, jid, password="", fingerprint=None):
		self.__fingerprint = binascii.unhexlify(fingerprint.encode('utf-8'))
		
		super().__init__(jid, password)
		
		self.register_plugin('extension_SVG', module='extension_SVG')
		
		self.add_event_handler('ssl_cert', self.__ssl_cert)
		self.add_event_handler('session_start', self.__session_start)
		self.add_event_handler('message', self.__message)
		self.add_event_handler('svg_message', self.__svg_message)
		self.add_event_handler('roster_update', self.__roster_update)
		self.add_event_handler('roster_update', self.__roster_update)
		self.add_event_handler('changed_status', self.__changed_status)
		self.add_event_handler('changed_subscription', self.__changed_subscription)
	
	def __ssl_cert(self, cert):
		print("ssl_cert ", cert)
		der = base64.b64decode(cert.split("-----")[2].encode('utf-8'))
		fingerprint = hashlib.sha256(der).digest()
		if (self.__fingerprint) and (self.__fingerprint != fingerprint):
			print("certificates do not match")
			self.disconnect()
		print(binascii.hexlify(fingerprint).decode('utf-8'))
	
	def __session_start(self, event):
		self.send_presence(pstatus="Laying around, gathering dust.", ppriority=0)
		self.get_roster()
	
	def __roster_update(self, roster):
		print("roster_update", roster)
	
	def __changed_status(self, presence):
		print("changed_status", presence)
	
	def __changed_subscription(self, presence):
		print("changed_subscription", presence)
	
	def __message(self, message):
		print("message", message)
	
	def __svg_message(self, svg):
		print("svg_message", svg)
	
	def exception(self, e):
		print(traceback.format_exc())




if __name__ == '__main__':
	import signal
	
	glib.threads_init()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	server = Server('haael@0nl1ne.cc/server', '0nl1ne.cc:12345', '7af9c66f25b4ed8e2f3a111be7970566e98c7ea7d303dac80956c40820dac219')
	
	try:
		server.connect()
		server.process()
		mainloop.run()
	except KeyboardInterrupt:
		print()
	finally:
		server.disconnect(wait=True)



