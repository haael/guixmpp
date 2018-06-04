#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import unicode_literals


from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

import slixmpp
import slixmpp.plugins.base
import slixmpp.stanza
import slixmpp.xmlstream
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.handler.base import BaseHandler
from slixmpp.xmlstream.matcher import MatchXPath
from slixmpp.xmlstream.matcher.base import MatcherBase



class SVGElement(slixmpp.xmlstream.ElementBase):
	namespace = 'http://www.w3.org/2000/svg'
	name = 'svg'
	plugin_attrib = 'svg'
	
	def init_from_string(self, xml):
		element = slixmpp.xmlstream.ET.fromstring(xml)
		if element.tag != self.name and element.tag != "".join(['{', self.namespace, '}', self.name]):
			raise ValueError("The supplied XML string must be an SVG document.")
		self.clear()
		for c in element:
			self.appendxml(c)
		return self
	
	def init_from_file(self, path):
		element = slixmpp.xmlstream.ET.parse(path).getroot()
		if element.tag != self.name and element.tag != "".join(['{', self.namespace, '}', self.name]):
			raise ValueError("The supplied file must be an XML/SVG document.")
		self.clear()
		for c in element:
			self.appendxml(c)
		return self


class extension_SVG(slixmpp.plugins.base.base_plugin):
	"""
	"""
	
	name = 'extension_SVG'
	
	def plugin_init(self):
		self.description = ""
		self.xep = 'x-SVG'
		self.svg = ""
		self.alpha = {}
		self.matrix = {}
		
		self.xmpp.register_handler(Callback('SVG', MatchXPath('{%s}message/{%s}svg' % (self.xmpp.default_ns, SVGElement.namespace)), self.__message))
		slixmpp.xmlstream.register_stanza_plugin(slixmpp.stanza.Message, SVGElement)
	
	def __message(self, msg):
		self.xmpp.event('svg_message', msg)
		
	def make_svg_string_message(self, mto, msvgstr, mbody=None):
		msg = self.xmpp.make_message(mto=mto)
		msg['svg'].init_from_string(msvgstr)
		if mbody is not None:
			msg['body'] = mbody
		return msg
	
	def send_svg_string(self, mto, msvgstr, mbody=None):
		self.make_svg_string_message(mto, msvgstr, mbody).send()
	
	def make_svg_file_message(self, mto, msvgfile, mbody=None):
		msg = self.xmpp.make_message(mto=mto)
		msg['svg'].init_from_file(msvgfile)
		if mbody is not None:
			msg['body'] = mbody
		return msg
	
	def send_svg_file(self, mto, msvgfile, mbody=None):
		self.make_svg_file_message(mto, msvgfile, mbody).send()
	
