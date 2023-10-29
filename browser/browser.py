#!/usr/bin/python3


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib, GdkPixbuf

#from locale import gettext
from mainloop import *
from domwidget import DOMWidget
from document import CreationError
from aiopath import Path
from asyncio import sleep


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
			raise AttributeError("Attribute not found in object nor in builder:" + attr)
	
	def replace_widget(self, name, new_widget):
		old_widget = getattr(self, name)
		parent = old_widget.get_parent()
		parent.remove(old_widget)
		parent.add(new_widget)
		setattr(self, name, new_widget)


class ListBoxWrapper:
	def __init__(self, container):
		self.__container = container
		self.__items = {}
	
	def index(self, item):
		return [_key for (_key, _value) in self.__items.items() if _value.main_widget is item][0]
	
	def clear(self):
		for child in self.__container.get_children():
			self.__container.remove(child)
		self.__items.clear()
	
	def select(self, name):
		item = self.__items[name].main_widget
		child = [_child for _child in self.__container.get_children() if _child.get_child() is item][0]
		self.__container.select_row(child)
	
	def keys(self):
		return self.__items.keys()
	
	def values(self):
		for value in self.__items.values():
			yield value.main_widget
	
	def items(self):
		for key, value in self.__items.items():
			yield key, value.main_widget
	
	def __getitem__(self, name):
		return self.__items[name]
	
	def __setitem__(self, name, item):
		self.__container.add(item.main_widget)
		self.__items[name] = item
		return item
	
	def __delitem__(self, name):
		item = self.__items[name].main_widget
		child = [_child for _child in self.__container.get_children() if _child.get_child() is item][0]
		self.__container.remove(child)
		del self.__items[name]


class Spinner:
	def __init__(self, disable_widgets):
		self.disable_widgets = disable_widgets
	
	def __enter__(self):
		for widget in self.disable_widgets:
			widget.props.sensitive = False
		return self
	
	def __exit__(self, *args):
		for widget in self.disable_widgets:
			widget.props.sensitive = True


class DataForm:
	def __init__(self, title, fields):
		grid = Gtk.Grid()
		grid.set_columns(3)
		grid.set_rows(len(fields) + 2)
		grid.pack_start(Gtk.Label(title), width=3)
		for descr, name, datatype in fields:
			grid.pack_start(Gtk.Label(descr))
			grid.pack_start(Gtk.Entry())
		box = Gtk.Box()
		grid.pack_start(box, width=3)
		box.pack_start(Gtk.Button("Cancel"))
		box.pack_end(Gtk.Button("Submit"))


class Browser(BuilderExtension):
	def __init__(self, interface, translation):
		super().__init__(interface, translation, ['window_main', 'entrybuffer_jid', 'popover_presence', 'filechooser_avatar', 'filefilter_images'], 'window_main')
		
		@asynchandler
		async def dom_event(widget, event):
			print(event)
			
			if event.type_ == 'opening':
				widget.main_url = event.detail
				widget.set_image(None)
			
			elif event.type_ == 'open':
				if event.detail == widget.main_url:
					widget.set_image(event.target)
				else:
					widget.set_image(widget.image)
			
			elif event.type_ == 'close':
				widget.main_url = None
				widget.set_image(None)
		
		size_request = self.drawingarea_avatar_preview.get_size_request()
		self.replace_widget('drawingarea_avatar_preview', DOMWidget(file_download=True))		
		self.drawingarea_avatar_preview.connect('dom_event', dom_event)		
		self.drawingarea_avatar_preview.set_size_request(*size_request)
		self.drawingarea_avatar_preview.show()
		
		size_request = self.drawingarea_avatar.get_size_request()
		self.replace_widget('drawingarea_avatar', DOMWidget(file_download=True))		
		self.drawingarea_avatar.connect('dom_event', dom_event)		
		self.drawingarea_avatar.set_size_request(*size_request)
		self.drawingarea_avatar.show()
		
		self.network_spinner = Spinner([self.form_login, self.form_register, self.form_server_options])
		self.stack_main.set_visible_child_name('page1')
	
	@asynchandler
	async def login(self, widget):
		with self.network_spinner:
			print("login", widget, self.entrybuffer_jid.get_text(), self.entry_login_password.get_text())
			await sleep(2)
	
	@asynchandler
	async def register(self, widget):
		with self.network_spinner:
			print("register", widget, self.entrybuffer_jid.get_text(), self.entry_registration_password_1.get_text(), self.entry_registration_password_2.get_text())
			await sleep(2)
	
	def choose_presence(self, widget):
		self.popover_presence.show()
	
	def choose_avatar(self, widget):
		self.filechooser_avatar.show()
	
	def cancel_avatar(self, widget, sthelse=None):
		print("cancel avatar")
		self.filechooser_avatar.hide()
		return True # cancel widget destroy
	
	def unset_avatar(self, widget):
		print("unset avatar")
		self.filechooser_avatar.hide()
		if self.drawingarea_avatar_preview.main_url:
			self.drawingarea_avatar_preview.close_document()
			self.drawingarea_avatar_preview.main_url = None
	
	@asynchandler
	async def select_avatar(self, widget):
		filename = self.filechooser_avatar.get_filename()
		if filename and not (await Path(filename).is_dir()):
			print("select avatar", filename, self.drawingarea_avatar_preview.main_url)
			if self.drawingarea_avatar_preview.main_url:
				self.drawingarea_avatar_preview.close_document()
				self.drawingarea_avatar_preview.main_url = None
			
			try:
				await self.drawingarea_avatar_preview.open_document(Path(filename).as_uri())
			except CreationError:
				self.drawingarea_avatar_preview.main_url = None
	
	@asynchandler
	async def set_avatar(self, widget):
		filename = self.filechooser_avatar.get_filename()
		if filename and not (await Path(filename).is_dir()):
			print("set avatar", filename, self.drawingarea_avatar)
			if self.drawingarea_avatar.main_url:
				self.drawingarea_avatar.close_document()
				self.drawingarea_avatar.main_url = None
			
			try:
				await self.drawingarea_avatar.open_document(Path(filename).as_uri())
			except CreationError:
				self.drawingarea_avatar.main_url = None
		
		self.filechooser_avatar.hide()
	
	@asynchandler
	async def set_presence(self, widget):
		if widget.get_active():
			print(widget.props.name)
			await sleep(1/20)
			self.popover_presence.hide()


if __name__ == '__main__':
	import sys, signal
	from asyncio import run
	from locale import bindtextdomain, textdomain
	
	loop_init()
	
	translation = 'haael_svg_browser'
	bindtextdomain(translation, 'locale')
	textdomain(translation)
	
	browser = Browser('browser.glade', translation)
	
	async def main():
		browser.show()
		try:
			await loop_run()
		finally:
			browser.hide()
	
	browser.main_widget.connect('destroy', lambda window: loop_quit())
	signal.signal(signal.SIGTERM, lambda signum, frame: loop_quit())
	
	run(main())

