#!/usr/bin/python3


from logging import getLogger
logger = getLogger(__name__)


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib, GdkPixbuf


from path_editor import PathEditor
from guixmpp import *

from locale import gettext
from secrets import choice as random_choice
if not 'Path' in globals(): from aiopath import Path
from asyncio import sleep, Event, Lock, create_task
from lxml.etree import fromstring, tostring
from random import randint


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


def return_false(meth):
	def newm(*args):
		meth(*args)
		return False
	return newm


def return_true(meth):
	def newm(*args):
		meth(*args)
		return True
	return newm


class MainWindow(BuilderExtension):
	def __init__(self, interface, translation):
		super().__init__(interface, translation, ['window_main'], 'window_main')
		self.glade_interface = interface
		self.translation = translation
		
		for domwidget in self.all_children(DOMWidget):
			domwidget.connect('dom_event', self.svg_view_dom_event)
		
		self.path_editor = PathEditor()
		self.overlay_main.add_overlay(self.path_editor)
		self.path_editor.show()
	
	@asynchandler
	async def svg_view_dom_event(self, widget, event, target):
		"DOM event handler for non-interactive SVG widgets."
		
		if event.type_ == 'warning':
			logger.warning(f"{event}")
		
		if event.type_ == 'download':
			if event.detail.startswith('data:'):
				return True
			elif event.detail != widget.main_url:
				return False


if __name__ == '__main__':
	from logging import DEBUG, basicConfig
	basicConfig(level=DEBUG)
	logger.setLevel(DEBUG)
	
	logger.info("paint")
	
	import sys
	from asyncio import run, get_running_loop
	from locale import bindtextdomain, textdomain
	from guixmpp.domevents import Event as DOMEvent
	
	loop_init()
	
	translation = 'haael_svg_paint'
	bindtextdomain(translation, 'locale')
	textdomain(translation)
	
	window = MainWindow('paint.glade', translation)
	
	async def main():
		DOMEvent._time = get_running_loop().time
		
		await window.domwidget_main.open('file://./apu-shotgun.jpg')
		
		window.show()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		window.hide()
		
		for domwidget in window.all_children(DOMWidget):
			await domwidget.close()
	
	window.main_widget.connect('destroy', lambda window: loop_quit())
	
	run(main())

