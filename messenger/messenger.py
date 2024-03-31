#!/usr/bin/python3


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib, GdkPixbuf


from guixmpp import *


from locale import gettext
from secrets import choice as random_choice
from aiopath import Path
from asyncio import sleep, Condition


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
		box.pack_start(Gtk.Button(gettext("Cancel")))
		box.pack_end(Gtk.Button(gettext("Submit")))


class Browser(BuilderExtension):
	ERROR_ICON = 'error'
	WARNING_ICON = 'important'
	
	def __init__(self, interface, translation):
		super().__init__(interface, translation, ['window_main', 'entrybuffer_jid', 'popover_presence', 'filechooser_avatar', 'filefilter_images'], 'window_main')
		
		for widget_name in 'drawingarea_avatar_preview', 'drawingarea_avatar':
			size_request = getattr(self, widget_name).get_size_request()
			self.replace_widget(widget_name, DOMWidget(file_download=True))
			widget = getattr(self, widget_name)
			#widget.connect('dom_event', self.svg_view_dom_event)
			widget.set_size_request(*size_request)
			widget.show()
		
		self.network_spinner = Spinner([self.form_login, self.form_register, self.form_server_options])
		
		self.roster = []
		self.listbox_main.add(BuilderExtension(interface, translation, ['roster_start'], 'roster_start').main_widget)
		self.roster.append(('page_start', None))
		self.listbox_main.add(BuilderExtension(interface, translation, ['roster_start'], 'roster_start').main_widget)
		self.roster.append(('page_profile', None))
	
	@classmethod
	def validate_username(cls, username):
		if not all(_ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._" for _ch in username):
			raise ValueError("Characters allowed in username are: alphanumeric, dot, hyphen and underscore.")
	
	@classmethod
	def validate_host(cls, host):
		if not all(_ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._" for _ch in host):
			raise ValueError("Characters allowed in host are: alphanumeric, dot, hyphen and underscore.")
	
	@classmethod
	def validate_resource(cls, resource):
		if not all(_ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._" for _ch in resource):
			raise ValueError("Characters allowed in resource are: alphanumeric, dot, hyphen and underscore.")
	
	@classmethod
	def split_jid(cls, jid):
		try:
			username, rest = jid.split('@')
			host, *resource = rest.split('/')
		except ValueError:
			raise ValueError("JID valid format is: username@host.addr/optional-resource")
		
		cls.validate_username(username)
		cls.validate_host(host)
		
		if len(resource) == 0:
			return username, host, None
		elif len(resource) == 1:
			cls.validate_resource(resource[0])
			return username, host, resource[0]
		else:
			raise ValueError("Only 1 resource string allowed.")
	
	@asynchandler
	async def login(self, widget):
		if not self.entrybuffer_jid.get_text():
			self.entry_login_jid.grab_focus()
			self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.ERROR_ICON)
			self.entry_login_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide a JID."))
			return
		else:
			self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		try:
			username, host, resource = self.split_jid(self.entrybuffer_jid.get_text())
		except ValueError as error:
			self.entry_login_jid.grab_focus()
			self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.ERROR_ICON)
			self.entry_login_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		jid = username + '@' + host
		password = self.entry_login_password.get_text()
		
		alt_host = self.entry_host.get_text()
		if alt_host:
			try:
				self.validate_host(alt_host)
			except ValueError as error:
				self.entry_host.grab_focus()
				self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.ERROR_ICON)
				self.entry_host.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
				return
			else:
				self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
				host = alt_host
		else:
			self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		port = self.entry_port.get_text()
		if not port:
			port = self.entry_port.get_placeholder_text()
		
		with self.network_spinner:
			print("login", widget, jid, host, port)
			await sleep(2)
	
	@asynchandler
	async def register(self, widget):
		if not self.entrybuffer_jid.get_text():
			self.entry_registration_jid.grab_focus()
			self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.ERROR_ICON)
			self.entry_registration_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide a JID."))
			return
		else:
			self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		try:
			username, host, resource = self.split_jid(self.entrybuffer_jid.get_text())
		except ValueError as error:
			self.entry_registration_jid.grab_focus()
			self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.ERROR_ICON)
			self.entry_registration_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		if len(self.entry_registration_password_1.get_text()) < 8:
			self.entry_registration_password_1.grab_focus()
			self.entry_registration_password_1.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.ERROR_ICON)
			self.entry_registration_password_1.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide password at least 8 characters long."))
			return
		else:
			self.entry_registration_password_1.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		if self.entry_registration_password_1.get_text() != self.entry_registration_password_2.get_text():
			self.entry_registration_password_2.grab_focus()
			self.entry_registration_password_2.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.ERROR_ICON)
			self.entry_registration_password_2.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Passwords do not match."))
			return
		else:
			self.entry_registration_password_2.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		jid = username + '@' + host
		
		alt_host = self.entry_host.get_text()
		if alt_host:
			try:
				self.validate_host(alt_host)
			except ValueError as error:
				self.entry_host.grab_focus()
				self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.ERROR_ICON)
				self.entry_host.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
				return
			else:
				self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
				host = alt_host
		else:
			self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		port = self.entry_port.get_text()
		if not port:
			port = self.entry_port.get_placeholder_text()
		
		with self.network_spinner:
			
			print("register", widget, jid, host, port)
			await sleep(2)
	
	def choose_presence(self, widget):
		self.popover_presence.show()
	
	def choose_avatar(self, widget):
		"Open avatar selection dialog."
		self.filechooser_avatar.show()
	
	def cancel_avatar(self, widget, sthelse=None):
		"Close avatar selection dialog."
		self.filechooser_avatar.hide()
		return True # prevent widget destroy
	
	@asynchandler
	async def unset_avatar(self, widget):
		"Remove user avatar from network."
		await self.drawingarea_avatar.close()
		self.filechooser_avatar.hide()
	
	@asynchandler
	async def select_avatar(self, widget):
		"Show preview in avatar selection dialog."
		
		filename = self.filechooser_avatar.get_filename()
		if filename:
			if await Path(filename).is_file():
				await self.drawingarea_avatar_preview.open(Path(filename).as_uri())
			else:
				await self.drawingarea_avatar_preview.close()
	
	@asynchandler
	async def set_avatar(self, widget):
		"Publish user avatar over the network."
		
		filename = self.filechooser_avatar.get_filename()
		if filename and not (await Path(filename).is_dir()):
			await self.drawingarea_avatar.open(Path(filename).as_uri())
		
		self.filechooser_avatar.hide()
	
	@asynchandler
	async def set_presence(self, widget):
		if widget.get_active():
			print(widget.props.name)
			await sleep(1/20)
			self.popover_presence.hide()
	
	@asynchandler
	async def generate_password(self, widget):
		if widget.get_active():
			self.entry_registration_password_1.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_registration_password_1.set_text("")
			self.entry_registration_password_1.set_visibility(True)
			self.entry_registration_password_1.set_sensitive(False)
			wordlist = (await Path('wordlist.txt').read_text('utf-8')).split("\n")
			pwd = []
			for n in range(4):
				pwd.append(random_choice(wordlist).strip())
			self.entry_registration_password_1.set_text(" ".join(pwd))
		else:
			self.entry_registration_password_1.set_text("")
			self.entry_registration_password_1.set_visibility(False)
			self.entry_registration_password_1.set_sensitive(True)
	
	def entry_icon_press(self, widget, icon_pos, event):
		widget.set_icon_from_icon_name(icon_pos, None)
	
	def allow_legacy_ssl(self, widget):
		if widget.get_active():
			self.entry_port.set_placeholder_text('5223')
		else:
			self.entry_port.set_placeholder_text('5222')
	
	#@asynchandler
	#async def svg_view_dom_event(self, widget, event):
	#	"DOM event handler for non-interactive SVG widgets."
	#	
	#	if event.type_ == 'open':
	#		widget.set_image(event.target)
	#	
	#	elif event.type_ == 'close':
	#		widget.set_image(None)
	
	def roster_row_select(self, listview, listrow):
		page_name, *params = self.roster[listrow.get_index()]
		self.stack_main.set_visible_child_name(page_name)
		print("roster item selected:", page_name)


if __name__ == '__main__':
	import sys, signal
	from asyncio import run
	from locale import bindtextdomain, textdomain
	
	loop_init()
	
	translation = 'haael_svg_messenger'
	bindtextdomain(translation, 'locale')
	textdomain(translation)
	
	browser = Browser('messenger.glade', translation)
	
	async def main():
		browser.listbox_main.select_row(browser.listbox_main.get_row_at_index(0))
		browser.show()
		try:
			await loop_run()
		finally:
			browser.hide()
	
	browser.main_widget.connect('destroy', lambda window: loop_quit())
	signal.signal(signal.SIGTERM, lambda signum, frame: loop_quit())
	
	run(main())

