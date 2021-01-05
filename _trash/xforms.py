#!/usr/bin/python3
#-*- coding:utf-8 -*-


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject as gobject
from gi.repository import GLib as glib
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GdkPixbuf



class XForms(gtk.Container):
	__gtype_name__ = 'XForms'
	
	__gproperties__ = {
		'model' : (gobject.TYPE_PYOBJECT, "model", "", gobject.PARAM_READWRITE)
	}
	
	def do_get_property(self, prop):
		if prop.name == 'model':
			return self.get_model()
		else:
			raise AttributeError("Unknown property %s" % prop.name)
	
	def do_set_property(self, prop, value):
		if prop.name == 'model':
			self.set_model(value)
		else:
			raise AttributeError("Unknown property %s" % prop.name)
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.document = None
		self.model = None
	
	def set_document(self, document):
		self.document = document
		self.update_document()
	
	def get_document(self, document):
		return self.document
	
	def update_document(self):
		self.remove_all_children()
		self.process_node(self.document, self)
	
	def process_node(self, node, widget):
		if node.namespace == self.XFORMS:
			control = None
			
			if node.name == 'input':
				control = gtk.Entry()
			elif node.name == 'secret':
				control = gtk.Entry()
			elif node.name == 'textarea':
				control = gtk.TextArea()
			elif node.name == 'output':
				control = gtk.Label()
			elif node.name == 'upload':
				pass
			elif node.name == 'range':
				pass
			elif node.name == 'trigger':
				control = gtk.Button()
			elif node.name == 'submit':
				control = gtk.Button()
			elif node.name == 'select':
				pass
			elif node.name == 'select1':
				pass
			
			if control:
				widget.add(control)
				for child in node:
					self.process_node(node, control)
			else:
				for child in node:
					self.process_node(node, widget)
		
		elif node.type == 'TEXT':
			widget.add(gtk.Label(node.value))
		else:
			for child in node:
				self.process_node(node, widget)
	
	def set_model(self, model):
		self.model = model
		self.update_model()
	
	def get_model(self):
		return self.model
	
	def update_model(self):
		pass
	
	def do_child_type(self): # TODO
		return(gtk.Widget.get_type())



