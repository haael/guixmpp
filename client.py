#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import unicode_literals


import sys
import signal
import traceback

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import GObject as gobject
from gi.repository import GLib as glib
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GdkPixbuf

import base64
import binascii
import hashlib

import sleekxmpp

from repeat import Repeat


class ClientXMPP(sleekxmpp.ClientXMPP):
	def exception(self, e):
		print(traceback.format_exc())


class Client:
	def __init__(self, guipath='gui.glade', csspath='style.css'):
		css = gtk.CssProvider()
		css.load_from_path(csspath)
		gtk.StyleContext().add_provider_for_screen(gdk.Screen.get_default(), css, gtk.STYLE_PROVIDER_PRIORITY_USER)
		
		self.__builder = gtk.Builder()
		self.__builder.add_from_file(guipath)
		self.__builder.connect_signals(self)
		self.setup_login()
		
		self.__client = None
		self.__mainloop = None
	
	def show_message(self, *text):
		buf = self['textview_messages'].get_buffer()
		for line in text:
			buf.insert(buf.get_end_iter(), "\n" + line)
	
	def connect_client_signals(self):
		if self.__client:
			self.__client.add_event_handler('ssl_cert', self.ssl_cert)
			self.__client.add_event_handler('failed_auth', self.failed_auth)
			self.__client.add_event_handler('disconnected', self.disconnected)
			self.__client.add_event_handler('session_start', self.session_start)
			self.__client.add_event_handler('session_end', self.session_end)
			self.__client.add_event_handler('message', self.message)
			self.__client.add_event_handler('svg_message', self.svg_message)
			self.__client.add_event_handler('roster_update', self.roster_update)
			self.__client.add_event_handler('changed_status', self.changed_status)
			self.__client.add_event_handler('changed_subscription', self.changed_subscription)
	
	def setup_login(self):
		box_main = self['box_main']
		for child in box_main.get_children():
			box_main.remove(child)
		box_login = self['box_login']
		box_login.get_parent().remove(box_login)
		box_main.pack_start(box_login, True, True, 0)
	
	def setup_roster(self):
		box_main = self['box_main']
		for child in box_main.get_children():
			box_main.remove(child)
		scrolledwindow_roster = self['scrolledwindow_roster']
		scrolledwindow_roster.get_parent().remove(scrolledwindow_roster)
		box_main.pack_start(scrolledwindow_roster, True, True, 0)
		
		repeat_roster = Repeat()
		
		box = gtk.Box()
		box.set_orientation(gtk.Orientation.VERTICAL)
		
		jid_box = gtk.Box()
		jid_box.set_orientation(gtk.Orientation.HORIZONTAL)
		jid_box.set_name('jid_box')
		label_jid = gtk.Label()
		label_jid.set_name('jid')
		label_jid.props.justify = gtk.Justification.LEFT
		jid_box.pack_start(label_jid, False, False, 32)
		jid_box.pack_start(gtk.Label(), True, True, 0)
		box.pack_start(jid_box, False, False, 0)
		
		box1 = gtk.Box()
		box1.set_orientation(gtk.Orientation.HORIZONTAL)
		box1.set_name('box1')
		image_photo = gtk.Image()
		image_photo.set_name('photo')
		image_photo.set_size_request(128, 128)
		box1.pack_start(image_photo, False, False, 0)
		box2 = gtk.Box()
		box2.set_orientation(gtk.Orientation.HORIZONTAL)
		box2.set_name('box2')
		image_avail = gtk.Image()
		image_avail.set_name('avail')
		image_avail.set_size_request(32, 32)
		box2.pack_start(image_avail, False, False, 1)
		label_status = gtk.Label()
		label_status.set_name('status')
		box2.pack_start(label_status, False, False, 0)
		box2.pack_start(gtk.Label(), True, True, 0)
		box1.pack_start(box2, True, True, 10)
		box.pack_start(box1, True, True, 0)
		
		repeat_roster.add(box)
		
		pig_1_128 = GdkPixbuf.Pixbuf.new_from_file('img/pig_1.png').scale_simple(128,128, GdkPixbuf.InterpType.BILINEAR)
		pig_2_128 = GdkPixbuf.Pixbuf.new_from_file('img/pig_2.png').scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
		pig_1_32 = GdkPixbuf.Pixbuf.new_from_file('img/pig_1.png').scale_simple(32, 32, GdkPixbuf.InterpType.BILINEAR)
		pig_2_32 = GdkPixbuf.Pixbuf.new_from_file('img/pig_2.png').scale_simple(32, 32, GdkPixbuf.InterpType.BILINEAR)
		
		model = []
		model.append({'box1.box2.avail.pixbuf':pig_1_32, 'box1.photo.pixbuf':pig_1_128, 'jid_box.jid.label':"haael@jabber.at",  'box1.box2.status.label':"Krtań lufy pusta łaknie znów pocisków smaku."})
		model.append({'box1.box2.avail.pixbuf':pig_2_32, 'box1.photo.pixbuf':pig_2_128, 'jid_box.jid.label':"haael@0nl1ne.cc",  'box1.box2.status.label':"When you raise your hands to the sunshine light..."})
		model.append({'box1.box2.avail.pixbuf':pig_1_32, 'box1.photo.pixbuf':None,      'jid_box.jid.label':"paula@freelab.cc", 'box1.box2.status.label':"Jazz na ulicach."})
		repeat_roster.set_model(model)

		scrolledwindow_roster.add(repeat_roster)
		#box_main.pack_start(repeat_roster, True, True, 0)
		
		repeat_roster.show_all()
		print("visibility:", repeat_roster.box.get_visible())
		
	
	def __getitem__(self, attr):
		return self.__builder.get_object(attr)
	
	def __getattr__(self, attr):
		def handle_event(widget, *args):
			if isinstance(widget, gtk.Buildable):
				name = gtk.Buildable.get_name(widget)
				kwargs = {}
				for a in ['name', 'visible', 'has-default', 'has-focus', 'is-focus', 'active']:
					try:
						kwargs[a] = widget.get_property(a)
					except TypeError:
						pass
				print(''.join([attr, '(', ', '.join([repr(_x) for _x in (name,) + args]), ', ', ', '.join([_x.replace('-', '_') + '=' + repr(_y) for (_x, _y) in kwargs.items()]), ')']))
			else:
				print(''.join([attr, '(', ', '.join([repr(_x) for _x in args])], ')'))
		handle_event.name = attr
		return handle_event
	
	def __jid_match(self, jid):
		try:
			username, rest = jid.split('@')
			forbidden_chars = [0x22, 0x26, 0x27, 0x2F, 0x3A, 0x3C, 0x3E, 0x40, 0x7F, 0xFFFE, 0xFFFF]
			if any(ord(ch) < 32 or ord(ch) in forbidden_chars for ch in username):
				return False
			domain, resource = rest.split('/')
			component = domain.split('.')
			if any(len(c) == 0 for c in component):
				return False
			if len(resource) == 0:
				return False
		except ValueError:
			return False
		return True
	
	def jid(self, widget, *args):
		entry_jid = self['entry_jid']
		jid = entry_jid.get_text()
		if len(jid) == 0 or self.__jid_match(jid):
			entry_jid.get_style_context().remove_class('invalid')
		else:
			entry_jid.get_style_context().add_class('invalid')
	
	def jid_ok(self, widget, *args):
		entry_jid = self['entry_jid']
		jid = entry_jid.get_text()
		if len(jid) > 0 and self.__jid_match(jid):
			entry_password = self['entry_password']
			entry_password.set_text("")
			entry_password.grab_focus()
			self.__client = ClientXMPP(jid, "")
			self.__client.anonymous_login = True
			self.connect_client_signals()
			self.__client.connect()
			self.__client.process()
	
	def ok(self, widget, *args):
		entry_jid = self['entry_jid']
		entry_password = self['entry_password']
		jid = entry_jid.get_text()
		if len(jid) > 0 and self.__jid_match(jid):
			pwd = entry_password.get_text()
			self.__client = ClientXMPP(jid, pwd)
			self.__client.anonymous_login = False
			self.connect_client_signals()
			self.__client.connect()
			self.__client.process()
		else:
			entry_jid.grab_focus()
		entry_password.set_text("")
	
	def ssl_cert(self, cert):
		print("ssl_cert")
		der = base64.b64decode(cert.split("-----")[2].encode('utf-8'))
		fingerprint = hashlib.sha256(der).digest()
		self.show_message("server certificate fingerprint:", " " + binascii.hexlify(fingerprint).decode('utf-8'))
	
	def failed_auth(self, ignore):
		print("failed_auth")
		if not self.__client.anonymous_login:
			self.show_message("invalid password")
		self.__client.disconnect()
	
	def session_start(self, ignore):
		print("session_start")
		entry_jid = self['entry_jid']
		entry_jid.set_editable(False)
		entry_jid.get_style_context().add_class('inactive')
	
	def session_end(self, ignore):
		print("session_end")
		entry_jid = self['entry_jid']
		entry_jid.set_editable(True)
		entry_jid.get_style_context().remove_class('inactive')
	
	def disconnected(self, ignore):
		print("disconnected")
		self.__client = None
	
	def disconnect(self):
		if self.__client:
			self.__client.disconnect()
	
	def destroy(self, window):
		if self.__mainloop:
			self.__mainloop.quit()
	
	def process(self):
		self.__mainloop = gobject.MainLoop()
		signal.signal(signal.SIGTERM, lambda signum, frame: self.__mainloop.quit())
		
		self.setup_roster()
		self['window'].show()
		
		try:
			self.__mainloop.run()
		except KeyboardInterrupt:
			print()
		finally:
			self.disconnect()


if __name__ == '__main__':
	glib.threads_init()
	Client().process()

