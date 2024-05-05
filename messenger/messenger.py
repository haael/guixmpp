#!/usr/bin/python3


from logging import getLogger
logger = getLogger(__name__)


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib, GdkPixbuf


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
	
	async def close_domwidgets(self):
		for domwidget in self.all_children(DOMWidget):
			await domwidget.close()


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


class SidebarContact(BuilderExtension):
	def __init__(self, interface, translation):
		super().__init__(interface, translation, ['sidebar_contact'], 'sidebar_contact')
		self.listbox_row = None
	
	def set_listbox_row(self, listbox_row):
		self.listbox_row = listbox_row
	
	def focus_entry(self, entry, event):
		self.listbox_row.get_parent().select_row(self.listbox_row)


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
	VALIDATION_ICON = 'important'
	BROKEN_CONNECTION_ICON = 'error'
	
	default_resource = 'guixmpp' # provide own branding
	
	def __init__(self, interface, translation):
		super().__init__(interface, translation, ['window_main', 'entrybuffer_jid', 'popover_presence', 'filechooser_avatar', 'filefilter_images'], 'window_main')
		self.glade_interface = interface
		self.translation = translation
		
		for widget_name in 'domwidget_avatar_preview', 'domwidget_avatar':
			domwidget = getattr(self, widget_name)
			domwidget.connect('dom_event', self.svg_view_dom_event)
		
		self.network_spinner = Spinner([self.form_login, self.form_register, self.form_server_options])
		
		self.sidebar_lock = Lock()
		
		self.sidebar = []
		self.listbox_main.add(BuilderExtension(interface, translation, ['sidebar_start'], 'sidebar_start').main_widget)
		self.sidebar.append(('page_start', None))
		
		self.paned_main.set_position(425)
		
		self.xmpp_connections = {}
	
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
			self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_login_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide a JID."))
			return
		else:
			self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		try:
			username, host, resource = self.split_jid(self.entrybuffer_jid.get_text())
		except ValueError as error:
			self.entry_login_jid.grab_focus()
			self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_login_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		if not resource:
			resource = self.default_resource
		jid = username + '@' + host + '/' + resource
		password = self.entry_login_password.get_text()
		self.entry_login_password.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		alt_host = self.entry_host.get_text()
		if alt_host:
			try:
				self.validate_host(alt_host)
			except ValueError as error:
				self.entry_host.grab_focus()
				self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
				self.entry_host.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
				return
			else:
				self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		else:
			self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			alt_host = None
		
		try:
			port = self.entry_port.get_text()
			if port:
				port = int(port)
				if not 0 < port <= 65535:
					raise ValueError("Port must be between 1 and 65535.")
			else:
				port = None
		except ValueError:
			self.entry_port.grab_focus()
			self.entry_port.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_port.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			self.entry_port.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		legacy_ssl = self.toggle_legacy_ssl.get_active()
		
		try:
			with self.network_spinner:
				await self.create_xmpp_connection(jid, alt_host, port, legacy_ssl, password, False)
		except ConnectionError as error:
			if self.entry_host.get_text():
				entry = self.entry_host
			else:
				entry = self.entry_login_jid			
			entry.grab_focus()
			entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
		except AuthenticationError as error:
			self.entry_login_password.grab_focus()
			self.entry_login_password.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			self.entry_login_password.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
	
	@asynchandler
	async def register(self, widget):
		if not self.entrybuffer_jid.get_text():
			self.entry_registration_jid.grab_focus()
			self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_registration_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide a JID."))
			return
		else:
			self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		try:
			username, host, resource = self.split_jid(self.entrybuffer_jid.get_text())
		except ValueError as error:
			self.entry_registration_jid.grab_focus()
			self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_registration_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		if len(self.entry_registration_password_1.get_text()) < 8:
			self.entry_registration_password_1.grab_focus()
			self.entry_registration_password_1.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_registration_password_1.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide password at least 8 characters long."))
			return
		else:
			self.entry_registration_password_1.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		if self.entry_registration_password_1.get_text() != self.entry_registration_password_2.get_text():
			self.entry_registration_password_2.grab_focus()
			self.entry_registration_password_2.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_registration_password_2.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Passwords do not match."))
			return
		else:
			self.entry_registration_password_2.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		if not resource:
			resource = self.default_resource
		jid = username + '@' + host + '/' + resource
		
		alt_host = self.entry_host.get_text()
		if alt_host:
			try:
				self.validate_host(alt_host)
			except ValueError as error:
				self.entry_host.grab_focus()
				self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
				self.entry_host.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
				return
			else:
				self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		else:
			self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			alt_host = None
		
		try:
			port = self.entry_port.get_text()
			if port:
				port = int(port)
				if not 0 < port <= 65535:
					raise ValueError("Port must be between 1 and 65535.")
			else:
				port = None
		except ValueError:
			self.entry_port.grab_focus()
			self.entry_port.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_port.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			self.entry_port.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		
		legacy_ssl = self.toggle_legacy_ssl.get_active()
		
		try:
			with self.network_spinner:
				await self.create_xmpp_connection(jid, alt_host, port, legacy_ssl, password, True)
		except ConnectionError as error:
			if self.entry_host.get_text():
				entry = self.entry_host
			else:
				entry = self.entry_registration_jid			
			entry.grab_focus()
			entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
	
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
		await self.domwidget_avatar.close()
		self.filechooser_avatar.hide()
	
	@asynchandler
	async def select_avatar(self, widget):
		"Show preview in avatar selection dialog."
		
		filename = self.filechooser_avatar.get_filename()
		if filename:
			if await Path(filename).is_file():
				await self.domwidget_avatar_preview.open(Path(filename).as_uri())
			else:
				await self.domwidget_avatar_preview.close()
	
	@asynchandler
	async def set_avatar(self, widget):
		"Publish user avatar over the network."
		
		filename = self.filechooser_avatar.get_filename()
		if filename and not (await Path(filename).is_dir()):
			await self.domwidget_avatar.open(Path(filename).as_uri())
		
		self.filechooser_avatar.hide()
	
	@asynchandler
	async def set_presence(self, widget):
		if widget.get_active():
			logger.debug(f"set presence: {widget.props.name}")
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
	
	@asynchandler
	async def svg_view_dom_event(self, widget, event, target):
		"DOM event handler for non-interactive SVG widgets."
		
		if event.type_ == 'warning':
			logger.warning(f"{event}")
		
		#if event.type_ == 'open':
		#	target.set_image(widget.model.get_document(event.target))
		#
		#elif event.type_ == 'close':
		#	target.set_image(None)
		
		if event.type_ == 'download':
			if event.detail.startswith('data:'):
				return True
			elif event.detail != widget.main_url:
				return False
	
	@asynchandler
	async def sidebar_row_select(self, listview, listrow):
		if listrow is None:
			return
		async with self.sidebar_lock:
			page_name, *params = self.sidebar[listrow.get_index()]
			self.stack_main.set_visible_child_name(page_name)
		logger.debug(f"sidebar item selected: {page_name}")
	
	async def create_xmpp_connection(self, jid, host, port, legacy_ssl, password, register):
		if jid in self.xmpp_connections:
			raise ValueError("Logged in already.")
		
		config = {}
		if host: config['host'] = host
		if port: config['port'] = port
		config['register'] = register
		config['legacy_ssl'] = legacy_ssl
		
		added = Event() # task object added to dictionary
		ready = get_running_loop().create_future() # connection established or failure
		
		sidebar_item = BuilderExtension(self.glade_interface, self.translation, ['sidebar_server'], 'sidebar_server')
		sidebar_item.entry_account_jid.set_text(jid)
		
		async def guarded_task():
			await added.wait()
			assert jid in self.xmpp_connections
			try:
				await self.xmpp_connection_task(ready, jid, password, config, sidebar_item)
			except Exception as error:
				if not ready.done(): # connected yet?
					ready.set_exception(error) # propagate early exceptions to `create_xmpp_connection`
				else:
					raise # propagage late exceptions to `destroy_xmpp_connection`
			finally:
				GLib.idle_add(return_false(self.destroy_xmpp_connection), jid)
		
		self.xmpp_connections[jid] = create_task(guarded_task())
		
		async with self.sidebar_lock:		
			self.listbox_main.add(sidebar_item.main_widget)
			self.sidebar.append(('page_server', jid))
			self.listbox_main.select_row(self.listbox_main.get_row_at_index(len(self.sidebar) - 1))
		
		logger.info("xmpp connection created")
		added.set()
		await ready # may raise exception from `guarded_task`
	
	@asynchandler
	async def destroy_xmpp_connection(self, jid):
		async with self.sidebar_lock:
			c = None
			for n, (label, njid) in enumerate(self.sidebar):
				if label == 'page_server' and njid == jid:
					c = n
					break
			assert c is not None
			self.listbox_main.remove(self.listbox_main.get_row_at_index(c))
			del self.sidebar[c]
		
		task = self.xmpp_connections[jid]
		del self.xmpp_connections[jid]
		await task # may raise exception from `guarded_task` TODO: show error popup
		logger.info("xmpp connection destroyed")
	
	async def xmpp_connection_task(self, ready, jid, password, config, sidebar_item):
		logger.debug(f"xmpp_connection_task {config}")
		
		async with XMPPClient(jid, config=config) as client:
			if not config['register']:
				client.password = password
			
			async for stanza in client:
				if stanza is None:
					continue
				elif hasattr(stanza, 'tag'):
					event_struct = await client.on_stanza(stanza)
					if event_struct is None:
						continue
					event, id_, from_, *elements = event_struct
					if event is None:
						continue
				else:
					event = stanza
				
				if event == 'ready':
					if not client.established:
						raise ConnectionError("Connection failed.")
					elif not client.authenticated:
						raise ConnectionError("Login failed or not attempted.")
					else:
						logger.info(f"Login successful: {jid}")
						ready.set_result(None) # mark login success
					
					@client.handle
					async def get_roster(expect):
						roster, = await client.query('get', None, fromstring('<query xmlns="jabber:iq:roster"/>'))
						sidebar_item.label_account_contacts.set_text(str(len(roster)))
						for item in roster:
							logger.debug(f"roster item: {tostring(item)}")
							contact_sidebar_item = await self.show_contact(jid, item.attrib['jid'])
							if contact_sidebar_item:
								try:
									contact_sidebar_item.entry_contact_name.set_text(item.attrib['name'])
								except KeyError:
									contact_sidebar_item.entry_contact_name.set_placeholder_text(item.attrib['jid'])
								contact_sidebar_item.domwidget_contact_avatar.set_property('file', f'assets/anon{randint(1, 11)}.jpeg')
						#client.stop()
				
				elif event == 'register':
					@client.handle
					async def register(expect):
						reg_query, = await client.query('get', None, fromstring('<query xmlns="jabber:iq:register"/>'))
						for child in reg_query:
							logger.debug(f"registration field: {tostring(child)}")
						client.stop()
						# TODO: fill out password
				
				else:
					logger.info(f"Ignored event: {event}")
	
	async def show_contact(self, server_jid, contact_jid):
		sidebar_item = SidebarContact(self.glade_interface, self.translation)
		
		async with self.sidebar_lock:
			c = None
			for n, (label, njid) in enumerate(self.sidebar):
				if label == 'page_server' and njid == server_jid:
					c = n
					break
			if c is None:
				return None
			
			for n, (label, njid) in enumerate(self.sidebar[c + 1:]):
				if label == 'page_server':
					break
				c += 1
			c += 1
			
			self.listbox_main.insert(sidebar_item.main_widget, c)
			self.sidebar.insert(c, ('page_contact', (server_jid, contact_jid)))
			sidebar_item.set_listbox_row(self.listbox_main.get_row_at_index(c))
			
			return sidebar_item


if __name__ == '__main__':
	import sys
	from logging import DEBUG, StreamHandler, basicConfig
	basicConfig(level=DEBUG)
	logger.setLevel(DEBUG)
	#logger.addHandler(StreamHandler())
	
	logger.debug("???")
	
	import sys, signal
	from asyncio import run, get_running_loop
	from locale import bindtextdomain, textdomain
	from guixmpp.domevents import Event as DOMEvent
	
	loop_init()
	
	translation = 'haael_svg_messenger'
	bindtextdomain(translation, 'locale')
	textdomain(translation)
	
	window = MainWindow('messenger.glade', translation)
	
	async def main():
		DOMEvent._time = get_running_loop().time
		
		window.listbox_main.select_row(window.listbox_main.get_row_at_index(0))
		window.show()
		try:
			await loop_run()
		finally:
			window.hide()
		await window.close_domwidgets()
	
	window.main_widget.connect('destroy', lambda window: loop_quit())
	signal.signal(signal.SIGTERM, lambda signum, frame: loop_quit())
	
	run(main())

