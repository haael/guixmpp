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
		self.register_plugin('extension_GTK', module='extension_GTK')
		
		self.add_event_handler('session_start', self.__session_start)
		self.add_event_handler('message', self.__message)
		self.add_event_handler('svg_result', self.__svg_result)
		self.add_event_handler('svg_error', self.__svg_error)
		self.add_event_handler('gui_interface', self.__gui_interface)
	
	def __session_start(self, event):
		print("session start")
		self.send_presence(pstatus="Slow change might bring holy tears.", ppriority=0)
	
	def __message(self, msg):
		print("message", msg['body'])
	
	def __svg_result(self, data):
		sid, iq = data
		print("svg_result", sid, iq)
	
	def __svg_error(self, data):
		sid, iq = data
		print("svg_error", sid, iq)
	
	def __gui_interface(self, data):
		jid, ui, menu = data
		self.windows[jid] = gui.handle_ui_description(self, jid, ui, menu)
		print("gui_description")
	
	def gui_open_application(self, jid):
		self['extension_GTK'].gtk_get_ui(jid)






if __name__ == '__main__':
	import signal
	import gui
	
	client = {}
	
	def connect(jid, password):
		if jid in client:
			disconnect(jid)
		client[jid] = Client(jid, password)
		client[jid].connect()
		client[jid].process()
	
	def disconnect(jid):
		client[jid].disconnect()
		del client[jid]
	
	glib.threads_init()
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	connect('haael@aqq.eu/9348702347', 'aqq.eu:12345')
	
	#with open("bunch.glade") as ui:
	#	gui.handle_ui_description(client, "haael@aqq.eu/micazook", ui.read())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	finally:
		while client:
			disconnect(client.pop())




