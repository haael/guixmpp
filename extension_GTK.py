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
		if element.tag != self.name
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
		if element.tag != self.name
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
	
	def add_event(self, name, *args):
		pass # model updates


class extension_GTK(sleekxmpp.plugins.base.base_plugin):
	"""
	"""
	
    def plugin_init(self):
        self.description = ""
        self.xep = 'x-GTK'
		
		#self.xmpp.registerHandler(Callback('Gtk Builder interface structure description', MatchXPath('{%s}message/{%s}interface' % (self.xmpp.default_ns, GtkIfElement.namespace)), self.__recv_if))
		#self.xmpp.registerHandler(Callback('Gtk UIManager interface behavior description', MatchXPath('{%s}message/{%s}ui' % (self.xmpp.default_ns, GtkUIElement.namespace)), self.__recv_ui))
		#sleekxmpp.xmlstream.register_stanza_plugin(sleekxmpp.stanza.Message, GtkIfElement)
		#sleekxmpp.xmlstream.register_stanza_plugin(sleekxmpp.stanza.Message, GtkUIElement)
		
		sleekxmpp.xmlstream.register_stanza_plugin(FormField, SVGElement)
		
		self.xmpp['xep_0050'].add_command(name="", node='get_ui', handler=self.__command)
		self.xmpp['xep_0050'].add_command(name="", node='get_if', handler=self.__command)
	
	def __command(self, iq, session):
		self.xmpp.event('gtk_command', iq)
		
		node = iq['command']['node']
		data = iq['command']['form']['fields']
		try:
			svgobject = data['obj']['value']
		except KeyError:
			svgobject = ''
		
		if node == 'get_ui':
			self.xmpp.event('gtk_get_ui')
		elif node == 'get_if':
			self.xmpp.event('gtk_get_if')
		else:
			pass # error
		
		return session
	
	def __cmd_next(self, iq, session):
		self.xmpp.event('gtk_result', (session['id'], iq['command']))
		self.xmpp['xep_0050'].complete_command(session)
	
	def __cmd_error(self, iq, session):
		self.xmpp.event('gtk_error', (session['id'], iq['command']))
	
	def __recv_if(self, msg):
		self.xmpp.event('gtk_if_message', msg)
	
	def __recv_ui(self, msg):
		self.xmpp.event('gtk_ui_message', msg)



