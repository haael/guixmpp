#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import unicode_literals


import sys

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
#from gi.repository import GdkPixbuf as gdk_pixbuf
from gi.repository import GLib as glib

import cairo
import rsvg

import base64
import hashlib

import sleekxmpp


class Client(sleekxmpp.ClientXMPP):
	def __init__(self, jid, password="", fingerprint=None):
		self.__fingerprint = fingerprint
		
		super().__init__(jid, password)
		
		self.register_plugin('extension_SVG', module='extension_SVG')
		self.register_plugin('extension_GTK', module='extension_GTK')
		
		self.add_event_handler('ssl_cert', self.__ssl_cert)
		self.add_event_handler('session_start', self.__session_start)
		self.add_event_handler('message', self.__message)
		self.add_event_handler('svg_result', self.__svg_result)
		self.add_event_handler('svg_error', self.__svg_error)
		self.add_event_handler('gui_interface', self.__gui_interface)
	
	def __ssl_cert(self, cert):
		print("ssl cert")
		der = base64.b64decode(cert.split("-----")[2].encode('utf-8'))
		fingerprint = hashlib.sha256(der).digest()
		if (self.__fingerprint) and (self.__fingerprint != fingerprint):
			# certificates do not match
			self.disconnect()
		print(fingerprint)
	
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


class Gui:
	def __init__(self, path, mainloop):
		self.path = path
		
		builder = gtk.Builder()
		builder.add_from_file(self.path)
		self.main_window = builder.get_object('main_window')
		self.main_window.connect('destroy', lambda window: mainloop.quit())
		self.main_notebook = builder.get_object('main_notebook')
		login_widget = builder.get_object('login_widget')
		login_widget.unparent()
		self.main_notebook.append_page(login_widget, gtk.Label("Logowanie"))
		
		self.jid_entry = builder.get_object('jid_entry')
		self.pwd_entry = builder.get_object('pwd_entry')
		self.srv_entry = builder.get_object('srv_entry')
		self.prx_entry = builder.get_object('prx_entry')
		
		self.cert_picture = builder.get_object('cert_picture')
		self.cert_textarea = builder.get_object('cert_textview')
		self.message_textarea = builder.get_object('messages_textview')
		
		builder.get_object('verify_button').connect('clicked', self.verify)
		builder.get_object('clear_button').connect('clicked', self.clear)
		builder.get_object('login_button').connect('clicked', self.login)
	
	def show(self):
		self.main_window.show()
		self.jid_entry.grab_focus()
	
	def verify(self, button):
		server = self.srv_entry.get_text()
		if server:
			try:
				address, port = server.split(":")
				port = int(port)
				server = (address, port)
			except ValueError:
				print("error in server value")
		else:
			server = ()
		connect(self.jid_entry.get_text(), server=server)
	
	def clear(self, button):
		self.jid_entry.set_text("")
		self.jid_entry.grab_focus()
		self.pwd_entry.set_text("")
		self.srv_entry.set_text("")
		self.prx_entry.set_text("")
	
	def login(self, button):
		server = self.srv_entry.get_text()
		if server:
			try:
				address, port = server.split(":")
				port = int(port)
				server = (address, port)
			except ValueError:
				print("error in server value")
		else:
			server = ()
		print(self.jid_entry.get_text(), self.pwd_entry.get_text())
		connect(self.jid_entry.get_text(), password=self.pwd_entry.get_text(), server=server)
	
	def roster(self, name, icons):
		builder = gtk.Builder()
		builder.add_objects_from_file(self.path, ['roster_window', 'roster_liststore', 'presence_liststore', 'adjustment1'])
		
		# setup icons
		edge = 24 # actual displayed icon size
		surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 64, 7 * 64)
		ctx = cairo.Context(surface)
		ctx.set_source_rgba(1, 1, 1, 0)
		ctx.paint()
		ctx.scale(edge / 64, edge / 64)
		handle = rsvg.Handle(path=bytes(icons, 'utf-8'))
		handle.render_cairo(ctx)
		surface.flush()
		
		presence_liststore = builder.get_object('presence_liststore')
		ls_iter = presence_liststore.get_iter_first()
		n = 0
		while ls_iter and presence_liststore.iter_is_valid(ls_iter):
			pixbuf = gdk.pixbuf_get_from_surface(surface, 0, edge * n, edge, edge)
			presence_liststore.set_value(ls_iter, 0, pixbuf)
			ls_iter = presence_liststore.iter_next(ls_iter)
			n += 1
		
		del ctx, handle, surface
		
		combo = builder.get_object('presence_combobox')
		crpb = gtk.CellRendererPixbuf()
		combo.pack_start(crpb, expand=False)
		combo.add_attribute(crpb, 'pixbuf', 0)
		crtx = gtk.CellRendererText()
		combo.pack_start(crtx, expand=False)
		combo.add_attribute(crtx, 'text', 1)
		
		roster_widget = builder.get_object('roster_widget')
		roster_widget.unparent()
		self.main_notebook.prepend_page(roster_widget, tab_label=gtk.Label(name))
		chats_notebook = builder.get_object('chats_notebook')
		
		builder = gtk.Builder()
		builder.add_objects_from_file(self.path, ['chat_window', 'chat_liststore'])
		chat = builder.get_object('chat_widget')
		chat.unparent()
		chats_notebook.append_page(chat, gtk.Label("jeden"))
		



		builder = gtk.Builder()
		builder.add_objects_from_file(self.path, ['chat_window', 'chat_liststore'])
		chat_iconview = builder.get_object('chat_iconview')
		chat_iconview.set_pixbuf_column(0)
		chat_iconview.set_text_column(1)
		# setup icons
		edge = 32 # actual displayed icon size
		surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 64, 7 * 64)
		ctx = cairo.Context(surface)
		ctx.set_source_rgba(1, 1, 1, 0)
		ctx.paint()
		ctx.scale(edge / 64, edge / 64)
		handle = rsvg.Handle(path=bytes(icons, 'utf-8'))
		handle.render_cairo(ctx)
		surface.flush()
		liststore = builder.get_object('chat_liststore')
		for n in range(7):
			pixbuf = gdk.pixbuf_get_from_surface(surface, 0, edge * n, edge, edge)
			liststore.append((pixbuf, str(n)))
			print(n)
		del ctx, handle, surface
		chat = builder.get_object('chat_widget')
		chat.unparent()
		chats_notebook.append_page(chat, gtk.Label("dwa"))
		


if __name__ == '__main__':
	import signal
	import gui
	
	client = {}
	
	def connect(jid, password="", server=(), proxy={}):
		if jid in client:
			disconnect(jid)
		cl = Client(jid, password)
		client[jid] = cl
		if proxy:
			cl.use_proxy = True
			cl.proxy_config = proxy
		cl.connect(address=server)
		cl.process()
	
	def disconnect(jid):
		client[jid].disconnect()
		del client[jid]
	
	glib.threads_init()
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	gui = Gui("gui.glade", mainloop)
	gui.show()
	gui.roster("Roster", "status_icons.svg")
	
	#connect("haael@aqq.eu/9348702347", "")
	
	#with open("bunch.glade") as ui:
	#	gui.handle_ui_description(client, "haael@aqq.eu/micazook", ui.read())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	finally:
		for c in [_c for _c in client.keys()]:
			disconnect(c)




