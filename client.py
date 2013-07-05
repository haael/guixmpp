#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import unicode_literals


import sys
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import GLib as glib

import sleekxmpp



class Client(sleekxmpp.ClientXMPP):
	def __init__(self, jid, password):
		super().__init__(jid, password)
		
		self.register_plugin('extension_SVG', module='extension_SVG')
		
		self.add_event_handler('session_start', self.__session_start)
		self.add_event_handler('message', self.__message)
		self.add_event_handler('svg_result', self.__svg_result)
		self.add_event_handler('svg_error', self.__svg_error)
	
	def __session_start(self, event):
		self.send_presence(pstatus="Slow change might bring holy tears.", ppriority=0)
		self.plugin['extension_SVG'].svg_send('haael@aqq.eu/juiz', 'AAAA', "<svg><el n='1111'/></svg>")
		self.plugin['extension_SVG'].svg_clear('haael@aqq.eu/juiz', 'BBBB')
		self.plugin['extension_SVG'].svg_send('haael@aqq.eu/juiz', 'CCCC', "<svg><el n='2222'/></svg>")
		self.plugin['extension_SVG'].svg_alpha('haael@aqq.eu/juiz', 'DDDD', 1.0)
		self.plugin['extension_SVG'].svg_matrix('haael@aqq.eu/juiz', 'DDDD', [1.0, 2.0, 3.0], [1,2,3,4,5,6,7,8,9])
		self.send_message(mto='haael@aqq.eu/juiz', mbody="bye")
	
	def __message(self, msg):
		print("message", msg['body'])
		if msg['body'] == 'f*ck':
			mainloop.quit()
	
	def __svg_result(self, data):
		sid, iq = data
		print("svg_result", sid, iq)
	
	def __svg_error(self, data):
		sid, iq = data
		print("svg_error", sid, iq)


if __name__ == '__main__':
	import signal
	
	glib.threads_init()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	client = Client('haael@aqq.eu/9348702347', 'aqq.eu:12345')
	client.connect()
	print("connected")
	
	try:
		client.process()
		print("main loop...")
		mainloop.run()
		print("main loop quit")
	except KeyboardInterrupt:
		print()
	finally:
		print("disconnect")
		client.disconnect(wait=True)
	print("quit")




