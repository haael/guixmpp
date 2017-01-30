#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import unicode_literals


import sys
import traceback

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import GObject as gobject
from gi.repository import GLib as glib
from gi.repository import Gtk as gtk

import base64
import binascii
import hashlib

import sleekxmpp


class Gui:
	def __init__(self, path='gui.glade'):
		self.builder = gtk.Builder()
		self.builder.add_from_file('gui.glade')
		self.window = builder.get_object('window')
	
	def login_mode(self):
		box_main = self.builder.get_object('box_main')
		box_login = self.builder.get_object('box_login')
		box_login.get_parent().remove(box_login)
		box_main.pack_start(box_login, True, True, 0)


if __name__ == '__main__':
	import signal
	
	glib.threads_init()
	
	#client = Client('haael@jabber.at/client', 'jabber.at:12345', '024c75330da703410e7ba9fde7be86f83465cf00c152b7985b668932d916060c')
	
	
	#client = Client('haael@0nl1ne.cc/client', '0nl1ne.cc:12345', '7af9c66f25b4ed8e2f3a111be7970566e98c7ea7d303dac80956c40820dac219')
	#client.connect()
	#client.process()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	
	#client.disconnect(wait=True)



