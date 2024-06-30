#!/usr/bin/python3


from logging import getLogger
logger = getLogger(__name__)


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib, GdkPixbuf


from guixmpp import *
from builder_extension import *
from dataforms import DataForm

from locale import gettext
from secrets import choice as random_choice
if not 'Path' in globals(): from aiopath import Path
from asyncio import sleep, Event, Lock, create_task, gather, wait, ALL_COMPLETED, FIRST_COMPLETED, CancelledError
from lxml.etree import fromstring, tostring
from random import randint
from os import environ, uname
from hashlib import sha3_256


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


class SidebarContact(BuilderExtension):
	def __init__(self, parent):
		super().__init__(parent, ['sidebar_contact'], 'sidebar_contact')
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


class Messenger(BuilderExtension):
	VALIDATION_ICON = 'important'
	BROKEN_CONNECTION_ICON = 'error'
	
	LOGIN_ICONS = 'chrome://login_validation.png', 'chrome://login_server.png', 'chrome://login_network.png'
	PRESENCE_ICONS = {'talkative':'chrome://presence_chat.png', 'online':'chrome://presence_online.png', 'busy':'chrome://presence_busy.png', 'away':'chrome://presence_away.png', 'offline':'chrome://presence_offline.png', 'error':'chrome://presence_error.png'}
	icon_width = 16
	icon_height = 16
	
	def __init__(self, interface, translation):
		class Props:
			glade_interface = interface
			gettext_translation = translation
			chrome_dir = Path('assets')
		
		BuilderExtension.__init__(self, Props(), ['window_main', 'entrybuffer_jid', 'filechooser_avatar', 'filefilter_images', 'popover_birthday', 'adjustment_talkative', 'adjustment_available', 'adjustment_busy', 'adjustment_away'], 'window_main')
		
		self.__tasks = set()
		self.__task_added = Event()
		
		self.network_spinner = Spinner([self.form_login, self.form_register, self.form_server_options, self.login_register_stackswitch])
		
		self.xmpp_servers = {}
		self.xmpp_contacts = {}
		self.sidebar_lock = Lock()
		self.sidebar = []
		start_item = BuilderExtension(self, ['sidebar_start'], 'sidebar_start')
		self.listbox_main.add(start_item.main_widget)
		self.sidebar.append(((), 'page_start', start_item))
		
		self.paned_main.set_position(445)
		
		self.xmpp_clients = {}
		self.foreground_server_jid = None
		self.global_presence = None
		self.global_status = "Kra kra kraj"
		
		self.ended = Event()
		self.registration_form_ok = Event()
		
		def on_destroy():
			logger.info("Main window closed.")
			self.ended.set()
		
		self.main_widget.connect('destroy', lambda messenger: on_destroy())
	
	resource_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	
	async def start(self):
		"Perform all startup tasks that require asyncio."
		
		u = uname()
		s = u.nodename + ":" + u.version + ":" + u.release + ":" + u.sysname + ":" + u.machine + ":" + "guixmpp_resource"
		d = sha3_256(s.encode('utf-8'))
		r = ''.join(self.resource_chars[_b % len(self.resource_chars)] for _b in d.digest())
		self.resource = r[:12]
		logger.info(f"Calculated resource: {self.resource}")
		
		self.toggle_save_login_password.set_sensitive(True)
		self.toggle_save_registration_password.set_sensitive(True)
		self.toggle_save_login_password.set_active(True)
		self.toggle_save_registration_password.set_active(True)
		
		presence_icons = [self.PRESENCE_ICONS[_status] for _status in ('talkative', 'online', 'busy', 'away', 'offline')]
		l_validation, l_server, l_network, s_chat, s_online, s_busy, s_away, s_offline = await gather(*[render_to_surface(self.icon_width, self.icon_height, _url, chrome=self.chrome_dir) for _url in list(self.LOGIN_ICONS) + presence_icons])
		
		self.login_validation_icon = Gdk.pixbuf_get_from_surface(l_validation, 0, 0, self.icon_width, self.icon_height)
		self.login_server_icon = Gdk.pixbuf_get_from_surface(l_server, 0, 0, self.icon_width, self.icon_height)
		self.login_network_icon = Gdk.pixbuf_get_from_surface(l_network, 0, 0, self.icon_width, self.icon_height)
		
		presence_chat_icon = Gdk.pixbuf_get_from_surface(s_chat, 0, 0, self.icon_width, self.icon_height)
		presence_online_icon = Gdk.pixbuf_get_from_surface(s_online, 0, 0, self.icon_width, self.icon_height)
		presence_busy_icon = Gdk.pixbuf_get_from_surface(s_busy, 0, 0, self.icon_width, self.icon_height)
		presence_away_icon = Gdk.pixbuf_get_from_surface(s_away, 0, 0, self.icon_width, self.icon_height)
		presence_offline_icon = Gdk.pixbuf_get_from_surface(s_offline, 0, 0, self.icon_width, self.icon_height)
		#self.presence_error_icon = Gdk.pixbuf_get_from_surface(s_error, 0, 0, self.icon_width, self.icon_height)
		
		self.get_widget_by_name(self.layout_presence, 'status_talkative').set_image(Gtk.Image.new_from_pixbuf(presence_chat_icon))
		self.get_widget_by_name(self.layout_presence, 'status_available').set_image(Gtk.Image.new_from_pixbuf(presence_online_icon))
		self.get_widget_by_name(self.layout_presence, 'status_busy').set_image(Gtk.Image.new_from_pixbuf(presence_busy_icon))
		self.get_widget_by_name(self.layout_presence, 'status_away').set_image(Gtk.Image.new_from_pixbuf(presence_away_icon))
		self.button_logout.set_image(Gtk.Image.new_from_pixbuf(presence_offline_icon))
		
		await self.sidebar[0][2].start()
		await super().start()
	
	async def stop(self):
		await super().stop()
		await self.sidebar[0][2].stop()
	
	async def __aenter__(self):
		await self.start()
		self.listbox_main.select_row(self.listbox_main.get_row_at_index(0))
		self.show()
		return self
	
	async def __aexit__(self, exctype, exception, traceback):
		self.hide()
		await self.stop()
		
		errors = []
		if self.__tasks:
			logger.warning("Some of tasks still running.")
			for task in self.__tasks:
				logger.debug(f" {task}")
			self.cancel()
			logger.debug("Waiting for remaining tasks to finish.")
			done, pending = await wait(self.__tasks, return_when=ALL_COMPLETED)
			assert not pending
			for task in done:
				try:
					await task
				except Exception as error:
					logger.error(f"Error cancelling task: ({type(exception).__name__}) {str(error)}")
					errors.append(error)
				except CancelledError:
					pass
		
		logger.info("Messenger exit.")
		
		if errors:
			if exception:
				raise ExceptionGroup("Error cancelling one of subtasks.", errors) from exception
			else:
				raise ExceptionGroup("Error cancelling one of subtasks.", errors)
	
	async def process(self):
		try:
			logger.info("Messenger main loop begin.")
			
			ended_task = self.create_task(self.ended.wait(), name='__check_if_loop_ended')
			task_added = None
			while not self.ended.is_set():
				if task_added is None:
					task_added = create_task(self.__task_added.wait(), name='__check_if_task_addded')
				done, pending = await wait(self.__tasks | frozenset({task_added}), return_when=FIRST_COMPLETED)
				
				if task_added.done():
					await task_added
					self.__task_added.clear()
					task_added = None
				
				for task in done:
					if task != task_added:
						await task
			
			if task_added is not None and not task_added.done():
				task_added.cancel()
			
			logger.info("Messenger main loop ended.")
		
		except BaseException as error:
			if not self.__tasks:
				raise
			logger.error(f"Error in Messenger mainloop: ({type(error).__name__}) {str(error)}")
			self.cancel()
			done, pending = await wait(self.__tasks, return_when=ALL_COMPLETED)
			assert not pending
			errors = []
			for task in done:
				try:
					await task
				except Exception as exception:
					logger.error(f"Error cancelling Messenger task: ({type(exception).__name__}) {str(exception)}")
					errors.append(exception)
				except CancelledError:
					pass
			if errors:
				raise ExceptionGroup("Error cancelling one of subtasks.", errors) from error
			else:
				raise
	
	def create_task(self, coro, name=None):
		logger.debug(f"Creating new task{ ' (' + name + ')' if name is not None else ''}.")
		task = create_task(coro, name=name)
		return self.wrap_task(task)
	
	def wrap_task(self, task):
		self.__tasks.add(task)
		task.add_done_callback(self.__tasks.discard)
		self.__task_added.set()
		return task
	
	def cancel(self):
		logger.info("Cancelling all tasks.")
		for task in self.__tasks:
			if not task.done():
				task.cancel()
	
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
			#self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_login_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
			self.entry_login_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide a JID."))
			return
		else:
			#self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_login_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		try:
			username, host, resource = self.split_jid(self.entrybuffer_jid.get_text())
		except ValueError as error:
			self.entry_login_jid.grab_focus()
			#self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_login_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
			self.entry_login_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			#self.entry_login_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_login_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		if not resource:
			resource = self.resource
		jid = username + '@' + host + '/' + resource
		password = self.entry_login_password.get_text()
		#self.entry_login_password.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
		self.entry_login_password.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		alt_host = self.entry_host.get_text()
		if alt_host:
			try:
				self.validate_host(alt_host)
			except ValueError as error:
				self.entry_host.grab_focus()
				#self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
				self.entry_host.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
				self.entry_host.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
				return
			else:
				#self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
				self.entry_host.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		else:
			#self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_host.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
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
			#self.entry_port.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_port.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
			self.entry_port.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			#self.entry_port.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_port.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		legacy_ssl = self.toggle_legacy_ssl.get_active()
		
		try:
			with self.network_spinner:
				await self.create_xmpp_connection(jid, alt_host, port, legacy_ssl, password, register=False)
		except (ConnectionError, AllConnectionAttemptsFailedError, TimeoutError) as error:
			if self.entry_host.get_text():
				entry = self.entry_host
			else:
				entry = self.entry_login_jid			
			entry.grab_focus()
			#entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			entry.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_network_icon)
			entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		except ProtocolError as error:
			if self.entry_host.get_text():
				entry = self.entry_host
			else:
				entry = self.entry_login_jid			
			entry.grab_focus()
			#entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			entry.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_server_icon)
			entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		except AuthenticationError as error:
			self.entry_login_password.grab_focus()
			#self.entry_login_password.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			self.entry_login_password.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_server_icon)
			self.entry_login_password.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		
		self.entry_login_jid.set_text("")
		self.entry_login_password.set_text("")
		self.entry_host.set_text("")
		self.entry_port.set_text("")
		self.toggle_legacy_ssl.set_active(False)
	
	@asynchandler
	async def register(self, widget):
		if not self.entrybuffer_jid.get_text():
			self.entry_registration_jid.grab_focus()
			#self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_registration_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
			self.entry_registration_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide a JID."))
			return
		else:
			#self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_registration_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		try:
			username, host, resource = self.split_jid(self.entrybuffer_jid.get_text())
		except ValueError as error:
			self.entry_registration_jid.grab_focus()
			#self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_registration_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
			self.entry_registration_jid.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			#self.entry_registration_jid.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_registration_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		if len(self.entry_registration_password_1.get_text()) < 8: # TODO: config
			self.entry_registration_password_1.grab_focus()
			#self.entry_registration_password_1.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_registration_password_1.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
			self.entry_registration_password_1.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Provide password at least 8 characters long."))
			return
		else:
			#self.entry_registration_password_1.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_registration_password_1.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		if self.entry_registration_password_1.get_text() != self.entry_registration_password_2.get_text():
			self.entry_registration_password_2.grab_focus()
			#self.entry_registration_password_2.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_registration_password_2.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
			self.entry_registration_password_2.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext("Passwords do not match."))
			return
		else:
			#self.entry_registration_password_2.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_registration_password_2.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		if not resource:
			resource = self.resource
		jid = username + '@' + host + '/' + resource
		password = self.entry_registration_password_2.get_text()
		
		alt_host = self.entry_host.get_text()
		if alt_host:
			try:
				self.validate_host(alt_host)
			except ValueError as error:
				self.entry_host.grab_focus()
				#self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
				self.entry_host.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
				self.entry_host.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
				return
			else:
				#self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
				self.entry_host.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		else:
			#self.entry_host.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_host.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
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
			#self.entry_port.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.VALIDATION_ICON)
			self.entry_port.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_validation_icon)
			self.entry_port.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			#self.entry_port.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_port.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		legacy_ssl = self.toggle_legacy_ssl.get_active()
		
		try:
			with self.network_spinner:
				await self.create_xmpp_connection(jid, alt_host, port, legacy_ssl, password, register=True)
		except (ConnectionError, AllConnectionAttemptsFailedError, TimeoutError) as error:
			if self.entry_host.get_text():
				entry = self.entry_host
			else:
				entry = self.entry_registration_jid
			entry.grab_focus()
			#entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			entry.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_network_icon)
			entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		except ProtocolError as error:
			if self.entry_host.get_text():
				entry = self.entry_host
			else:
				entry = self.entry_registration_jid
			entry.grab_focus()
			#entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			entry.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, self.login_server_icon)
			entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		else:
			self.entry_host.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_registration_jid.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
		
		self.entry_registration_jid.set_text("")
		self.entry_registration_password_1.set_text("")
		self.entry_registration_password_2.set_text("")
		self.entry_host.set_text("")
		self.entry_port.set_text("")
		self.toggle_legacy_ssl.set_active(False)
	
	def logout(self, widget):
		print("logout")
	
	@asynchandler
	async def presence_global_toggled(self, widget):
		self.xmpp_clients[self.foreground_server_jid].__global_presence = widget.get_active()
		
		if not widget.get_active(): return
		
		if self.xmpp_clients[self.foreground_server_jid].__presence != self.global_presence:
			self.xmpp_clients[self.foreground_server_jid].__presence = self.global_presence
			await self.update_presence()
	
	@asynchandler
	async def presence_switch(self, widget):
		if not widget.get_active(): return
		
		match widget.get_name():
			case 'status_talkative':
				presence = 'chat'
			case 'status_available':
				presence = None
			case 'status_busy':
				presence = 'dnd'
			case 'status_away':
				presence = 'xa'
			case _:
				raise ValueError
		
		current_local = self.xmpp_clients[self.foreground_server_jid].__presence
		current_global = self.global_presence
		use_global = self.togglebutton_presence_global.get_active()
		
		if use_global and current_global != presence:
			self.global_presence = presence
		
		if current_local != presence:
			self.xmpp_clients[self.foreground_server_jid].__presence = presence
		
		if current_local != presence or (use_global and current_global != presence):
			await self.update_presence()
	
	def priority_change(self, widget):
		print("priority change", widget)
	
	@asynchandler
	async def status_global_toggled(self, widget):
		self.xmpp_clients[self.foreground_server_jid].__global_status = widget.get_active()
		
		if not widget.get_active(): return
		
		if self.xmpp_clients[self.foreground_server_jid].__status != self.global_status:
			self.entry_status.set_text(self.global_status)
			self.xmpp_clients[self.foreground_server_jid].__status = self.global_status
			await self.update_presence()
	
	@asynchandler
	async def status_change(self, widget):
		new_status = self.entry_status.get_text()
		if self.xmpp_clients[self.foreground_server_jid].__status == new_status:
			return
		
		self.xmpp_clients[self.foreground_server_jid].__status = new_status
		if self.xmpp_clients[self.foreground_server_jid].__global_status:
			self.global_status = new_status
		
		await self.update_presence()
	
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
	
	async def update_presence(self):
		for client in self.xmpp_clients.values():
			if client.__global_presence:
				client.__presence = self.global_presence
			if client.__global_status:
				client.__status = self.global_status
		
		await gather(*[_client.presence(show=_client.__presence, status=_client.__status, priority=10) for _client in self.xmpp_clients.values()])
	
	def birthday_selected(self, widget):
		self.menubutton_birthday.set_active(False)
		y, m, d = widget.get_date()
		m += 1 # months in 'get_date' are 0 based (0 = January)
		self.entry_birthday.set_text(f"{y:04d}-{m:02d}-{d:02d}")
		self.entry_birthday.grab_focus()
	
	def birthday_show(self, widget):
		try:
			y, m, d = map(int, self.entry_birthday.get_text().split("-"))
		except (TypeError, ValueError) as error:
			logger.warning("Invalid birthday date format: " + self.entry_birthday.get_text())
		else:
			m -= 1 # months are 0 based
			self.calendar_birthday.select_month(m, y)
			self.calendar_birthday.select_day(d)
	
	def update_profile(self, widget):
		print("update_profile")
	
	@asynchandler
	async def generate_password(self, widget):
		if widget.get_active():
			#self.entry_registration_password_1.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_registration_password_1.set_icon_from_pixbuf(Gtk.EntryIconPosition.PRIMARY, None)
			self.entry_registration_password_1.set_text("")
			self.entry_registration_password_1.set_visibility(True)
			self.entry_registration_password_1.set_sensitive(False)
			
			# TODO: config
			dictionary_path = Path(f'wordlist.{environ["LANGUAGE"]}.txt') # use LANGUAGE environment variable
			if not await dictionary_path.exists():
				dictionary_path = Path('wordlist.en.txt') # default to English dictionary if no locale found
			
			wordlist = (await dictionary_path.read_text('utf-8')).split("\n")
			pwd = []
			for n in range(4):
				pwd.append(random_choice(wordlist).strip())
			self.entry_registration_password_1.set_text(" ".join(pwd))
		else:
			self.entry_registration_password_1.set_text("")
			self.entry_registration_password_1.set_visibility(False)
			self.entry_registration_password_1.set_sensitive(True)
	
	def entry_icon_press(self, widget, icon_pos, event):
		#widget.set_icon_from_icon_name(icon_pos, None) # hide error icon when it's clicked on
		widget.set_icon_from_pixbuf(icon_pos, None) # hide error icon when it's clicked on
	
	def allow_legacy_ssl(self, widget):
		if widget.get_active():
			self.entry_port.set_placeholder_text('5223')
		else:
			self.entry_port.set_placeholder_text('5222')
	
	@asynchandler
	async def dom_event(self, widget, event, target):
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
			key, page_name, sidebar_item = self.sidebar[listrow.get_index()]
			await self.show_main_page(page_name, key, sidebar_item)
		logger.debug(f"sidebar item selected: {page_name}")
	
	def get_widget_by_name(self, parent, name):
		for child in parent.get_children():
			if child.get_name() == name:
				return child
		else:
			raise KeyError(f"Child not found: {name}")
	
	async def show_main_page(self, page_name, key, sidebar_item):
		if page_name == 'page_server':
			self.foreground_server_jid = key[0]
			self.foreground_contact_jid = None
			
			client = self.xmpp_clients[self.foreground_server_jid]
			self.togglebutton_presence_global.set_active(client.__global_presence)
			match client.__presence:
				case 'chat':
					self.get_widget_by_name(self.layout_presence, 'status_talkative').set_active(True)
				case 'dnd':
					self.get_widget_by_name(self.layout_presence, 'status_busy').set_active(True)
				case 'xa':
					self.get_widget_by_name(self.layout_presence, 'status_away').set_active(True)
				case _:
					self.get_widget_by_name(self.layout_presence, 'status_available').set_active(True)
			
			self.togglebutton_status_global.set_active(client.__global_status)
			self.entry_status.set_text(client.__status)
			
			self.entry_profile_jid.set_text(self.foreground_server_jid)
			self.entry_nickname.set_text(client.__nickname)
		
		elif page_name == 'page_contact':
			self.foreground_server_jid = key[0]
			self.foreground_contact_jid = key[1]
			
			self.paned_contact.set_position(self.paned_contact.get_allocated_height() - 150)
		
		else:
			self.foreground_server_jid = None
			self.foreground_contact_jid = None
		
		#if page_name == 'page_contact':
		#	server_jid, contact_jid = params
		#	
		#	message_box = BuilderExtension(self.glade_interface, self.gettext_translation, ['message_box'], 'message_box')
		#	
		#	for domwidget in message_box.all_children(DOMWidget):
		#		domwidget.model.create_resource = self.create_resource
		#		domwidget.model.chrome_dir = Path('assets')
		#		domwidget.connect('dom_event', self.dom_event)
		#	
		#	if randint(0, 2) != 0:
		#		message_box.message_nick.set_visible(False)
		#		message_box.message_avatar.set_visible(False)
		#	message_box.message_control.set_visible(False)
		#	self.listbox_chat.add(message_box.main_widget)
		
		self.stack_main.set_visible_child_name(page_name)
	
	def paned_contact_moved(self, widget):
		print("paned_contact_moved", widget.get_position())
	
	def paned_contact_resized(self, widget, event):
		print("paned_contact_resized", event)
		self.paned_contact.set_position(self.paned_contact.get_allocated_height() - 150)	
	
	async def registration_form(self, data, client):
		if hasattr(self, '_Messenger__registration_form'):
			raise ValueError("Registration form already in operation.")
		
		parent = self
		
		class Config:
			def xmpp_client(self, domwidget):
				return client
			
			def __getattr__(self, attr):
				return getattr(parent, attr)
			
			@asynchandler
			async def dom_event(self, widget, event, target):
				if event.type_ == 'open':
					image = target.model.current_document(target)
					w, h = target.model.image_dimensions(widget, image)
					widget.set_size_request(w, h) # adjust DOMWidget size to the displayed image size
		
		registration_form = DataForm(Config())
		self.registration_form_bin.add(registration_form.main_widget)
		registration_form.show()
		await registration_form.start()
		await registration_form.add_data(data)
		self.registration_form_frame.show()
		
		done, pending = await wait([create_task(registration_form.completed.wait(), name='__completed_wait'), create_task(self.ended.wait(), name='__ended_wait')], return_when=FIRST_COMPLETED)
		for task in pending:
			task.cancel()
		
		self.registration_form_frame.hide()
		await registration_form.stop()
		self.registration_form_bin.remove(registration_form.main_widget)
		
		for task in done:
			await task
		
		return registration_form.proceed
	
	def registration_form_understood_clicked(self, widget):
		self.registration_form_ok.set()
	
	async def create_xmpp_connection(self, jid, host, port, legacy_ssl, password, register):
		if jid in self.xmpp_clients:
			raise ValueError("Logged in already.")
		
		logger.debug("Creating new XMPP connection.")
		
		config = {}
		if host: config['host'] = host
		if port: config['port'] = port
		config['register'] = register
		config['legacy_ssl'] = legacy_ssl
		
		async def xmpp_task(ready, register):
			retry = 1
			while True:
				retry -= 1
				try:
					async with XMPPClient(jid, config=config) as client:
						client.password = password
						
						if not register:
							logger.debug("XMPP login.")
							await client.login()
						else:
							logger.debug("XMPP register.")
							form = await client.register()
							
							if instructions := form.xpath('xep-0077:instructions', namespaces=client.namespace):
								self.registration_form_instructions.set_text(instructions[0].text)
								self.registration_form_instructions.show()
							
							if regform := form.xpath('xep-0004:x', namespaces=client.namespace):
								from base64 import b64decode # TODO
								for medium in form.xpath('xep-0231:data', namespaces=client.namespace):
									#print("set_resource", medium)
									client.set_resource(medium.attrib['cid'], b64decode(medium.text), medium.attrib['type'])
								proceed = await self.registration_form(regform[0], client)
							elif (userfield := form.xpath('xep-0077:username', namespaces=client.namespace)) and (passwordfield := form.xpath('xep-0077:password', namespaces=client.namespace)):
								userfield[0].text = jid.split('@')[0]
								passwordfield[0].text = password
								if form.xpath('xep-0077:email', namespaces=client.namespace):
									email_form = fromstring(f'<x xmlns="jabber:x:data" type="form"><field type="text-single" label="{gettext("Email address")}" var="email"><required/></field></x>')
									proceed = await self.registration_form(email_form, client)
									form.xpath('xep-0077:email', namespaces=client.namespace)[0].text = email_form.xpath('xep-0004:field[@var="email"]', namespaces=client.namespace)[0].text
								else:
									proceed = True
							else:
								self.registration_form_ok.clear()
								self.registration_form_understood.show()
								await self.registration_form_ok.wait()
								proceed = False
							
							self.registration_form_instructions.hide()
							self.registration_form_understood.hide()
							
							if not proceed:
								break
							result = await client.iq_set(jid.split('@')[1].split('/')[0], form)
							register = False
						
						client.__global_presence = True
						client.__global_status = True
						client.__presence = self.global_presence
						client.__status = self.global_status
						client.__nickname = ""
						self.xmpp_clients[jid] = client
						
						try:
							await self.add_sidebar_server(jid)
							await self.select_sidebar_item(jid)
							
							logger.debug("XMPP connection ready.")
							ready.set() # mark login success
							retry = 3 # TODO: config
							
							@client.task
							async def message(client):
								while (stanza := await client.expect('self::client:message')) is not None:
									await self.message(client, stanza)
							
							@client.task
							async def presence(client):
								while (stanza := await client.expect('self::client:presence')) is not None:
									await self.presence(client, stanza)
							
							roster = await client.iq_get(None, fromstring(f'<query xmlns="{client.namespace["iq-roster"]}"/>'))
							for item in roster.xpath('iq-roster:item', namespaces=client.namespace):
								await self.add_sidebar_contact(jid, item.attrib['jid'], item.attrib.get('name', None))
							
							await self.update_presence()
							
							#last_query = fromstring(f'<query xmlns="{client.namespace["xep-0012"]}"/>')
							#for contact_jid in roster.xpath('iq-roster:item/@jid', namespaces=client.namespace):
							#	last = await client.iq_get(contact_jid, last_query)
							#	print(" last", tostring(last))
							#last_result = await gather(*[client.iq_get(_jid, last_query) for _jid in roster.xpath('iq-roster:item/@jid', namespaces=client.namespace)])
							#for last in last_result:
							#	print(" last", tostring(last))
							
							await client.process()
						
						finally:
							logger.debug("XMPP cleanup...")
							await client.presence(type_='unavailable', status=client.__status)
							await self.remove_sidebar_item(jid)
							del self.xmpp_clients[jid]
				
				except ConnectionError as error:
					logger.error(f"Connection error in XMPP client: {error}")
					# TODO: display warning, configure option
					
					if retry > 0:
						logger.info("Retrying...")
						continue # retry
					else:
						raise
				
				else:
					break
		
		ready = Event()
		task = create_task(xmpp_task(ready, register), name=f'jid:{jid}')
		wait_for_ready = create_task(ready.wait(), name='__wait_for_ready')
		wait_for_ended = create_task(self.ended.wait(), name='__wait_for_ended')
		await wait([task, wait_for_ready, wait_for_ended], return_when=FIRST_COMPLETED)
		logger.debug(f"XMPP connection creation: ready: {wait_for_ready.done()}; connection done: {task.done()}; ended: {wait_for_ended.done()}.")
		
		if not wait_for_ended.done():
			wait_for_ended.cancel()
		else:
			if not wait_for_ready.done():
				wait_for_ready.cancel()
			ready.set()
			await task # should exit gracefully
			logger.debug("XMPP connection creation ended.")
			return
		
		if not ready.is_set():
			ready.set()
			await wait_for_ready
			
			if not task.done():
				task.cancel()
			else:
				await task
		else:
			await wait_for_ready
			self.wrap_task(task)
		
		logger.debug("XMPP connection creation done.")
	
	async def add_sidebar_item(self, key, page_name, item):
		async with self.sidebar_lock:
			parent_key = key[:-1]
			found = False
			for n, (n_key, _, _) in enumerate(self.sidebar):
				if not found and n_key == parent_key:
					found = True
				elif found and len(n_key) == len(parent_key) and n_key != parent_key:
					break
			
			n += 1
			
			self.listbox_main.insert(item.main_widget, n)
			self.sidebar.insert(n, (key, page_name, item))
			
			if hasattr(item, 'start'):
				await item.start()
			
			return self.listbox_main.get_row_at_index(n)
	
	async def remove_sidebar_item(self, *key):
		async with self.sidebar_lock:
			pos_todel = []
			child_todel = set()
			
			unselect = False
			parent_key = key[:-1]
			p = 0
			sel = self.listbox_main.get_selected_row()
			for n, (n_key, _, _) in enumerate(self.sidebar):
				if parent_key == n_key:
					p = n
				elif key == n_key[:len(key)]:
					pos_todel.append(n)
					child = self.listbox_main.get_row_at_index(n)
					if child is not None: # child may be None during destroy
						child_todel.add(child)
					if child == sel:
						unselect = True
			
			if unselect:
				self.listbox_main.select_row(self.listbox_main.get_row_at_index(p))
			
			items_tostop = []
			for n in reversed(pos_todel):
				_, _, item = self.sidebar[n]
				items_tostop.append(item)
				del self.sidebar[n]
			await gather(*[_item.stop() for _item in items_tostop if hasattr(_item, 'stop')])
			
			for child in child_todel:
				self.listbox_main.remove(child)
	
	async def select_sidebar_item(self, *key):
		async with self.sidebar_lock:
			p = None
			for n, (n_key, _, _) in enumerate(self.sidebar):
				if key == n_key:
					p = n
					break
			if p is not None:
				self.listbox_main.select_row(self.listbox_main.get_row_at_index(p))
	
	async def selected_sidebar_key(self):
		async with self.sidebar_lock:
			sel = self.listbox_main.get_selected_row()
			for n, key in enumerate(self.sidebar):
				el = self.listbox_main.get_row_at_index(n)
				if sel == el:
					return key
			else:
				return None
	
	async def update_sidebar_item(self, *key):
		if await self.selected_sidebar_key() == key:
			await self.select_sidebar_item(*key)
	
	async def add_sidebar_server(self, server_jid):
		"Create sidebar item for the new connection."
		sidebar_item = BuilderExtension(self, ['sidebar_server'], 'sidebar_server')
		sidebar_item.entry_account_jid.set_text(server_jid)
		return await self.add_sidebar_item((server_jid,), 'page_server', sidebar_item)
	
	async def add_sidebar_contact(self, server_jid, contact_jid, contact_name=None):
		sidebar_item = SidebarContact(self)
		
		listbox_row = await self.add_sidebar_item((server_jid, contact_jid), 'page_contact', sidebar_item)
		sidebar_item.set_listbox_row(listbox_row)
		await sidebar_item.domwidget_contact_presence.open(self.PRESENCE_ICONS['offline'])
		
		if contact_name:
			sidebar_item.entry_contact_name.set_text(contact_name)
		else:
			sidebar_item.entry_contact_name.set_placeholder_text(contact_jid)
		
		await sidebar_item.domwidget_contact_avatar.open(f'resource://guixmpp/jabber-avatar?account={server_jid}&contact={contact_jid}')
		
		return listbox_row
	
	async def create_resource(self, model, url):
		scheme, realm, server, *path = url.split('/')
		assert scheme == 'resource:'
		assert realm == ''
		assert server == 'guixmpp'
		path = '/'.join(path)
		path, *query = path.split('?')
		query = '?'.join(query)
		query = dict(_q.split('=') for _q in query.split('&'))
		
		if path == 'jabber-avatar':
			return await self.get_jabber_avatar(model, query['account'], query['contact'])
		else:
			return None, 'application/x-null'
	
	async def get_jabber_avatar(self, model, account_jid, contact_jid):
		client = self.xmpp_clients[account_jid]
		assert client.jid == account_jid
		return await model.download_document(f'chrome://anon{randint(1, 11)}.jpeg')
	
	async def message(self, client, stanza):
		print(" message", tostring(stanza))
	
	async def presence(self, client, stanza):
		print(" presence", tostring(stanza))


if __name__ == '__main__':
	from logging import DEBUG, INFO, basicConfig
	from sys import argv
	
	if '--verbose' in argv[1:]:
		basicConfig(level=DEBUG)
		logger.setLevel(DEBUG)
	else:
		basicConfig(level=INFO)
		logger.setLevel(INFO)
	
	logger.info("messenger")
	
	from asyncio import run, get_running_loop
	from locale import bindtextdomain, textdomain
	from guixmpp.domevents import Event as DOMEvent
	
	translation = 'haael_svg_messenger'
	bindtextdomain(translation, 'locale')
	textdomain(translation)
	
	loop_init()
	
	async def main():
		DOMEvent._time = get_running_loop().time
		async with Messenger('messenger.glade', translation) as messenger:
			await messenger.process()
	
	try:
		run(loop_main(main()))
	except KeyboardInterrupt:
		pass

