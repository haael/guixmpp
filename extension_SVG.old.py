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



class SVGElement(sleekxmpp.xmlstream.ElementBase):
	namespace = 'http://www.w3.org/2000/svg'
	name = 'svg'
	plugin_attrib = 'svg'
	
	def init_from_xml(self, xml):
		element = sleekxmpp.xmlstream.ET.fromstring(xml)
		if element.tag != self.name and element.tag != "".join(['{', self.namespace, '}', self.name]):
			raise ValueError("The supplied XML string must be an SVG document.")
		self.clear()
		for c in element:
			self.appendxml(c)
		return self
	
	def init_from_file(self, path):
		print(path)
		element = sleekxmpp.xmlstream.ET.parse(path).getroot()
		print(element)
		print(element.tag, self.name)
		if element.tag != self.name and element.tag != "".join(['{', self.namespace, '}', self.name]):
			raise ValueError("The supplied XML string must be an SVG document.")
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
	
	def mod_subobject_params(self, name, alpha=None, shift=None, rotation=None):
		raise NotImplementedError()
		return self


class extension_SVG(sleekxmpp.plugins.base.base_plugin):
	"""
	"""
	
	name = 'extension_SVG'
	dependencies = set(['xep_0004', 'xep_0050'])
	
	def plugin_init(self):
		self.description = ""
		self.xep = 'x-SVG'
		self.svg = ""
		self.alpha = {}
		self.matrix = {}
		
		self.xmpp.register_handler(Callback('SVG', MatchXPath('{%s}message/{%s}svg' % (self.xmpp.default_ns, SVGElement.namespace)), self.__message))
		sleekxmpp.xmlstream.register_stanza_plugin(sleekxmpp.stanza.Message, SVGElement)
		sleekxmpp.xmlstream.register_stanza_plugin(FormField, SVGElement)
		
		self.xmpp['xep_0050'].add_command(name="Create or update an SVG object", node='svg_send', handler=self.__command)
		self.xmpp['xep_0050'].add_command(name="Show an SVG object", node='svg_show', handler=self.__command)
		self.xmpp['xep_0050'].add_command(name="Hide an SVG object", node='svg_hide', handler=self.__command)
		self.xmpp['xep_0050'].add_command(name="Set an SVG object transparency", node='svg_alpha', handler=self.__command)
		self.xmpp['xep_0050'].add_command(name="Set an SVG object transformation matrix", node='svg_matrix', handler=self.__command)
		self.xmpp['xep_0050'].add_command(name="Clear and remove an SVG object", node='svg_clear', handler=self.__command)
	
	def __message(self, msg):
		self.xmpp.event('svg_message', msg)
		
		self.svg = str(msg['svg'])
		self.svg_alpha = {}
		self.svg_matrix = {}
		
		self.xmpp.event('svg_update', (self.svg, self.svg_alpha, self.svg_matrix))
	
	def __command(self, iq, session):
		self.xmpp.event('svg_command', iq)
		
		node = iq['command']['node']
		data = iq['command']['form']['fields']
		try:
			svgobject = data['obj']['value']
		except KeyError:
			svgobject = ''
		
		if node == 'svg_send':
			xml = data['svg']['svg']
			self.xmpp.event('svg_send', (svgobject, xml))
			
			# self.svg['#' + svgobject] = xml
			# self.svg = xml
		elif node == 'svg_clear':
			self.xmpp.event('svg_clear', svgobject)
			
			# del self.svg['#' + svgobject]
			# self.svg = None
		elif node == 'svg_show':
			self.xmpp.event('svg_show', svgobject)
			
			self.alpha[svgobject] = 1.0
		elif node == 'svg_hide':
			self.xmpp.event('svg_hide', svgobject)
			
			self.alpha[svgobject] = 0.0
		elif node == 'svg_alpha':
			alpha = float(data['alpha']['value'])
			self.xmpp.event('svg_alpha', (svgobject, alpha))
			
			self.alpha[svgobject] = alpha
		elif node == 'svg_matrix':
			shift = [float(_x) for _x in data['shift']['value'].split(',')]
			rotation = [float(_x) for _x in data['rotation']['value'].split(',')]
			self.xmpp.event('svg_matrix', (svgobject, shift, rotation))
			
			self.matrix[svgobject] = shift, rotation
		else:
			pass # error
		
		self.xmpp.event('svg_update', (self.svg, self.alpha, self.matrix))
		return session
	
	def __cmd_next(self, iq, session):
		self.xmpp.event('svg_result', (session['id'], iq['command']))
		self.xmpp['xep_0050'].complete_command(session)
		
		# for multi-part commands:
		#self.xmpp['xep_0050'].continue_command(session)
		#self.xmpp['xep_0050'].cancel_command(session)
	
	def __cmd_error(self, iq, session):
		self.xmpp.event('svg_error', (session['id'], iq['command']))
	
	def make_svg_string_message(self, mto, msvg, mbody=None):
		msg = self.xmpp.make_message(mto=mto)
		msg['svg'].init_from_xml(msvg)
		if mbody is not None:
			msg['body'] = mbody
		return msg
	
	def send_svg_string(self, mto, msvg, mbody=None):
		self.make_svg_string_message(mto, msvg, mbody).send()
	
	def make_svg_file_message(self, mto, msvgfile, mbody=None):
		msg = self.xmpp.make_message(mto=mto)
		msg['svg'].init_from_file(msvgfile)
		if mbody is not None:
			msg['body'] = mbody
		return msg
	
	def send_svg_file(self, mto, msvgfile, mbody=None):
		self.make_svg_file_message(mto, msvgfile, mbody).send()
	
	def svg_send_string(self, jid, obj, svg):
		print("send_svg_string")
		form = self.xmpp['xep_0004'].make_form()
		form.add_field(var='obj', ftype='str', value=obj)
		form.add_field(var='svg', ftype='svg')['svg'].init_from_xml(svg)
		
		session = {'payload':[form], 'next':self.__cmd_next, 'error':self.__cmd_error}
		self.xmpp['xep_0050'].start_command(jid=jid, node='svg_send', session=session)
		return session['id']
	
	def svg_send_file(self, jid, obj, svg):
		print("send_svg_file " + svg)
		form = self.xmpp['xep_0004'].make_form()
		form.add_field(var='obj', ftype='str', value=obj)
		form.add_field(var='svg', ftype='svg')['svg'].init_from_file(svg)
		
		session = {'payload':[form], 'next':self.__cmd_next, 'error':self.__cmd_error}
		self.xmpp['xep_0050'].start_command(jid=jid, node='svg_send', session=session)
		return session['id']
	
	def svg_clear(self, jid, obj=''):
		form = self.xmpp['xep_0004'].make_form()
		form.add_field(var='obj', ftype='str', value=obj)
		
		session = {'payload':[form], 'next':self.__cmd_next, 'error':self.__cmd_error}
		self.xmpp['xep_0050'].start_command(jid=jid, node='svg_clear', session=session)
		return session['id']
	
	def svg_show(self, jid, obj):
		form = self.xmpp['xep_0004'].make_form()
		form.add_field(var='obj', ftype='str', value=obj)
		
		session = {'payload':[form], 'next':self.__cmd_next, 'error':self.__cmd_error}
		self.xmpp['xep_0050'].start_command(jid=jid, node='svg_show', session=session)
		return session['id']
	
	def svg_hide(self, jid, obj):
		form = self.xmpp['xep_0004'].make_form()
		form.add_field(var='obj', ftype='str', value=obj)
		
		session = {'payload':[form], 'next':self.__cmd_next, 'error':self.__cmd_error}
		self.xmpp['xep_0050'].start_command(jid=jid, node='svg_hide', session=session)
		return session['id']
	
	def svg_alpha(self, jid, obj, alpha):
		form = self.xmpp['xep_0004'].make_form()
		form.add_field(var='obj', ftype='str', value=obj)
		form.add_field(var='alpha', ftype='str', value=str(alpha))
		
		session = {'payload':[form], 'next':self.__cmd_next, 'error':self.__cmd_error}
		self.xmpp['xep_0050'].start_command(jid=jid, node='svg_alpha', session=session)
		return session['id']
	
	def svg_matrix(self, jid, obj, shift, rotation):
		form = self.xmpp['xep_0004'].make_form()
		form.add_field(var='obj', ftype='str', value=obj)
		form.add_field(var='shift', ftype='str', value=','.join([str(_x) for _x in shift]))
		form.add_field(var='rotation', ftype='str', value=','.join([str(_x) for _x in rotation]))
		
		session = {'payload':[form], 'next':self.__cmd_next, 'error':self.__cmd_error}
		self.xmpp['xep_0050'].start_command(jid=jid, node='svg_matrix', session=session)
		return session['id']



