#!/usr/bin/python3


__all__ = 'BuilderExtension',


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from asyncio import gather
from .domwidget import DOMWidget


class BuilderExtension:
	def __init__(self, parent, objects, main_widget_name):
		self.__parent = parent
		self.__builder = Gtk.Builder()
		self.__objects = objects
		self.__main_widget_name = main_widget_name
	
	@property
	def builder_parent(self):
		return self.__parent
	
	@property
	def main_widget(self):
		#print("retrieve main widget", self.__main_widget_name)
		return getattr(self, self.__main_widget_name)
	
	@property
	def glade_interface(self):
		return self.builder_parent.glade_interface
	
	@property
	def gettext_translation(self):
		return self.builder_parent.gettext_translation
	
	@property
	def create_resource(self):
		return self.builder_parent.create_resource
	
	@property
	def dom_event(self):
		return self.builder_parent.dom_event
	
	@property
	def chrome_dir(self):
		return self.builder_parent.chrome_dir
	
	@property
	def xmpp_client(self):
		return self.builder_parent.xmpp_client
	
	def get_application(self):
		return self.__builder.get_application()
	
	def set_application(self, app):
		return self.__builder.set_application(app)
	
	def show(self):
		self.main_widget.show()
	
	def hide(self):
		self.main_widget.hide()
	
	def __getattr__(self, attr):
		widget = self.__builder.get_object(attr)
		if widget != None:
			#setattr(self, attr, widget)
			return widget
		else:
			raise AttributeError("Attribute not found in object nor in builder: " + attr)
	
	def replace_widget(self, name, new_widget):
		old_widget = getattr(self, name)
		parent = old_widget.get_parent()
		parent.remove(old_widget)
		parent.add(new_widget)
		setattr(self, name, new_widget)
	
	def all_children(self, type_=Gtk.Widget):
		def iter_children(widget):
			if isinstance(widget, type_):
				yield widget
			if not hasattr(widget, 'get_children'):
				return
			for child in widget.get_children():
				yield from iter_children(child)
		yield from iter_children(self.main_widget)
	
	async def start(self):
		self.__builder.set_translation_domain(self.gettext_translation)
		interface = self.glade_interface
		#print("builder start", self.__objects, interface)
		text = await interface.read_text()
		#print("xml", text)
		self.__builder.add_objects_from_string(text, self.__objects)
		self.__builder.connect_signals(self)
		
		for domwidget in self.all_children(DOMWidget):
			if domwidget.cid_download:
				domwidget.model.set_xmpp_client(self.xmpp_client(domwidget))
			domwidget.model.create_resource = self.create_resource
			domwidget.model.chrome_dir = self.chrome_dir
			domwidget.connect('dom_event', self.dom_event)
		
		await gather(*[_domwidget.open('') for _domwidget in self.all_children(DOMWidget)])
	
	async def stop(self):
		await gather(*[_domwidget.close() for _domwidget in self.all_children(DOMWidget)])

