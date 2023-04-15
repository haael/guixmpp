#!/usr/bin/python3
#-*- coding:utf-8 -*-


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
		if element.tag != f'{{{self.namespace}}}{self.name}':
			raise ValueError("The supplied string must be an XML/SVG document.")
		self.clear()
		for c in element:
			self.appendxml(c)
		return self
	
	def init_from_file(self, path):
		element = slixmpp.xmlstream.ET.parse(path).getroot()
		if element.tag != f'{{{self.namespace}}}{self.name}':
			raise ValueError("The supplied path must point to an XML/SVG document.")
		self.clear()
		for c in element:
			self.appendxml(c)
		return self


class extension_SVG(slixmpp.plugins.base.base_plugin):
	name = 'extension_SVG'
	
	def plugin_init(self):
		self.description = ""
		self.xep = 'x-SVG'
		
		self.xmpp.register_handler(Callback('SVG', MatchXPath(f'{{{self.xmpp.default_ns}}}message/{{{SVGElement.namespace}}}svg', self.__message))
		slixmpp.xmlstream.register_stanza_plugin(slixmpp.stanza.Message, SVGElement)
	
	def __message(self, msg):
		self.xmpp.event('svg_message', msg)
	
	def make_svg_string_message(self, mto, msvgstr, mbody=None):
		msg = self.xmpp.make_message(mto=mto)
		msg['svg'].init_from_string(msvgstr)
		if mbody != None:
			msg['body'] = mbody
		return msg
	
	def send_svg_string(self, mto, msvgstr, mbody=None):
		self.make_svg_string_message(mto, msvgstr, mbody).send()
	
	def make_svg_file_message(self, mto, msvgfile, mbody=None):
		msg = self.xmpp.make_message(mto=mto)
		msg['svg'].init_from_file(msvgfile)
		if mbody != None:
			msg['body'] = mbody
		return msg
	
	def send_svg_file(self, mto, msvgfile, mbody=None):
		self.make_svg_file_message(mto, msvgfile, mbody).send()


