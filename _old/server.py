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
		
		self.add_event_handler('session_start', self.start)
		self.add_event_handler('message', self.message)
		#self.add_event_handler('svg_message', self.svg_message)
		#self.add_event_handler('svg_command', self.svg_command)
		self.add_event_handler('svg_update', self.svg_update)
		self.add_event_handler('svg_append', self.svg_append)
		self.add_event_handler('svg_send', self.svg_send)
		self.add_event_handler('svg_clear', self.svg_clear)
		self.add_event_handler('svg_alpha', self.svg_alpha)
		self.add_event_handler('svg_matrix', self.svg_matrix)
	
	def start(self, event):
		self.send_presence(pstatus="Slow change might bring holy tears.", ppriority=0)
	
	def svg_message(self, msg):
		print()
		print("svg_message:", msg)
	
	def svg_command(self, iq):
		print()
		print("svg_command:", iq)
	
	def svg_update(self, args):
		print("svg_update:", args)
		print()
	
	def svg_append(self, svg):
		print("svg_append:", svg)
	
	def svg_clear(self, svg):
		print("svg_clear:", svg)
	
	def svg_send(self, param):
		(svg, xml) = param
		print("svg_send:", svg, xml)
	
	def svg_alpha(self, param):
		(svg, alpha) = param
		print("svg_alpha:", svg, alpha)
	
	def svg_matrix(self, param):
		(svg, shift, rotation) = param
		print("svg_matrix:", svg, shift, rotation)
	
	def message(self, msg):
		print("message:", msg)
		msg.reply()
		msg['body'] = "f*ck"
		msg.send()


if __name__ == '__main__':
	import signal
	
	glib.threads_init()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	client = Client('haael@aqq.eu/juiz', 'aqq.eu:12345')
	client.connect()
	
	try:
		client.process()
		mainloop.run()
	except KeyboardInterrupt:
		print()
	finally:
		client.disconnect(wait=True)






