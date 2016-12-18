#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import unicode_literals


from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

import sleekxmpp
import sleekxmpp.plugins.base
import sleekxmpp.stanza
import sleekxmpp.xmlstream
from sleekxmpp.plugins.xep_0004.stanza.form import FormField
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.handler.base import BaseHandler
from sleekxmpp.xmlstream.matcher import MatchXPath
from sleekxmpp.xmlstream.matcher.base import MatcherBase



class GtkIfElement(sleekxmpp.xmlstream.ElementBase):
	namespace = 'gtk:userinterface'
	name = 'interface'
	plugin_attrib = 'gtk_if'
	
	def init_from_xml(self, xml):
		element = sleekxmpp.xmlstream.ET.fromstring(xml)
		if element.tag != self.name:
			raise ValueError("The supplied XML string must be a GTK interface document.")
		self.clear()
		for c in element:
			self.appendxml(c)
		return self
	
	def add_subtree(self, name, xml):
		raise NotImplementedError()
		return self
	
	def get_subobject(self, name):
		raise NotImplementedError()
		pass
	
	def del_subobject(self, name, xml):
		raise NotImplementedError()
		return self


class GtkUIElement(sleekxmpp.xmlstream.ElementBase):
	namespace = 'gtk:userinterface'
	name = 'ui'
	plugin_attrib = 'gtk_ui'
	
	def init_from_xml(self, xml):
		element = sleekxmpp.xmlstream.ET.fromstring(xml)
		if element.tag != self.name:
			raise ValueError("The supplied XML string must be a GTK ui document.")
		self.clear()
		for c in element:
			self.appendxml(c)
		return self
	
	def add_subtree(self, name, xml):
		raise NotImplementedError()
		return self
	
	def get_subobject(self, name):
		raise NotImplementedError()
		pass
	
	def del_subobject(self, name, xml):
		raise NotImplementedError()
		return self


class GtkEvent(sleekxmpp.xmlstream.ElementBase):
	namespace = 'gtk:userinterface'
	name = 'event'
	plugin_attrib = 'gtk_event'
	
	def add_event(self, widget, name, args, kwargs):
		pass
		return self
	
	def add_delta(self, delta):
		pass
		return self


class extension_GTK(sleekxmpp.plugins.base.base_plugin):
	"""
	"""
	
	def plugin_init(self):
		self.description = ""
		self.xep = 'x-GTK'
		self.servers = {}
		self.clients = {}
		
		self.xmpp.register_handler(Callback('Gtk event', MatchXPath('{%s}message/{%s}event' % (self.xmpp.default_ns, GtkEvent.namespace)), self.__message))
		sleekxmpp.xmlstream.register_stanza_plugin(sleekxmpp.stanza.Message, GtkEvent)
		
		sleekxmpp.xmlstream.register_stanza_plugin(FormField, GtkIfElement)
		sleekxmpp.xmlstream.register_stanza_plugin(FormField, GtkUIElement)
		
		self.xmpp['xep_0050'].add_command(name="", node='gtk_open_application', handler=self.__command)
		
		self.xmpp.add_event_handler('gui_emit_signal', self.__gui_emit_signal)
		self.xmpp.add_event_handler('gui_update_model', self.__gui_update_model)
		self.xmpp.add_event_handler('gui_close_application', self.__gui_close_application)
	
	def set_ui(self, ui, menu):
		self.ui = ui
		self.menu = menu
	
	def __command(self, iq, session):
		self.xmpp.event('gtk_command', iq)
		
		if iq['command']['node'] == 'gtk_open_application':
			form = iq['command']['form']
			form.add_field(var='ui', ftype='gtk_if')['gtk_if'].init_from_xml(self.ui)
			form.add_field(var='menu_count', ftype='int', value=len(self.menu))
			for n, menu in enumerate(self.menu):
				form.add_field(var='menu' + str(n), ftype='gtk_ui')['gtk_ui'].init_from_xml(menu)
			#self.xmpp.event('gtk_open_application', (jid, ui, menu))
		else:
			pass # error
		
		return session
	
	def __cmd_next(self, iq, session):
		self.xmpp.event('gtk_result', (session['id'], iq['command']))
		self.xmpp['xep_0050'].complete_command(session)
	
	def __cmd_error(self, iq, session):
		self.xmpp.event('gtk_error', (session['id'], iq['command']))
	
	def __message(self, msg):
		self.xmpp.event('gtk_if_message', msg)
	
	def open_application(self, jid):
		#form = self.xmpp['xep_0004'].make_form()
		#form.add_field(var='obj', ftype='str', value=obj)
		#form.add_field(var='svg', ftype='svg')['svg'].init_from_xml(svg)
		
		session = {'payload':[], 'next':self.__cmd_next, 'error':self.__cmd_error}
		self.xmpp['xep_0050'].start_command(jid=jid, node='gtk_get_if', session=session)
		return session['id']
	
	def make_event_message(self, mto, widget, name, args, kwargs, mbody=None):
		msg = self.xmpp.make_message(mto=mto)
		msg['gtk_event'].add_event(widget, name, args, kwargs)
		if mbody is not None:
			msg['body'] = mbody
		return msg
	
	def send_event_message(self, mto, widget, name, args, kwargs, mbody=None):
		self.make_event_message(mto, widget, name, args, kwargs, mbody).send()
	
	def make_delta_message(self, mto, delta, mbody=None):
		msg = self.xmpp.make_message(mto=mto)
		msg['gtk_event'].add_delta(delta)
		if mbody is not None:
			msg['body'] = mbody
		return msg
	
	def send_delta_message(self, mto, delta, mbody=None):
		self.make_event_message(mto, delta, mbody).send()
	
	def __gui_emit_signal(self, data):
		jid, widget, name, args, kwargs = data
		#print("gui_emit_signal", widget, name, args, kwargs)
		self.send_event_message(jid, widget, name, args, kwargs)
	
	def __gui_update_model(self, data):
		jid, delta = data
		#print("gui_update_model", delta)
		self.send_delta_message(jid, delta)
	
	def __gui_close_application(self, jid):
		del self.servers[jid]
		print("gui_close_application", jid)



