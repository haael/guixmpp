#!/usr/bin/python3


__all__ = 'BuilderExtension',


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

#from guixmpp import DOMWidget


class BuilderExtension:
	def __init__(self, interface, translation, objects, main_widget_name):
		self.__builder = Gtk.Builder()
		self.__builder.set_translation_domain(translation)
		self.__builder.add_objects_from_file(interface, objects)
		self.__builder.connect_signals(self)
		self.__main_widget_name = main_widget_name
	
	@property
	def main_widget(self):
		return getattr(self, self.__main_widget_name)
	
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
	
	#async def close_domwidgets(self):
	#	for domwidget in self.all_children(DOMWidget):
	#		await domwidget.close()

