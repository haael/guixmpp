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


'''
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
'''


class SidebarContact(BuilderExtension):
	def __init__(self, parent):
		super().__init__(parent, ['sidebar_contact'], 'sidebar_contact')
		self.listbox_row = None
		
		#for domwidget in self.all_children(DOMWidget):
		#	domwidget.model.create_resource = parent.create_resource
		#	domwidget.model.chrome_dir = parent.chrome_dir
		#	domwidget.connect('dom_event', parent.dom_event)
	
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
	
	default_resource = 'guixmpp' # provide own branding
	
	def __init__(self, interface, translation):
		class Props:
			glade_interface = interface
			gettext_translation = translation
			chrome_dir = Path('assets')
		
		BuilderExtension.__init__(self, Props(), ['window_main', 'entrybuffer_jid', 'popover_presence', 'filechooser_avatar', 'filefilter_images'], 'window_main')
		
		self.__tasks = set()
		self.__task_added = Event()
		
		self.network_spinner = Spinner([self.form_login, self.form_register, self.form_server_options])
		
		self.xmpp_servers = {}
		self.xmpp_contacts = {}
		self.sidebar_lock = Lock()
		self.sidebar = []
		start_item = BuilderExtension(self, ['sidebar_start'], 'sidebar_start')
		self.listbox_main.add(start_item.main_widget)
		self.sidebar.append(((), 'page_start', start_item))
		
		self.paned_main.set_position(425)
		
		self.xmpp_clients = {}
		
		self.ended = Event()
		
		def on_destroy():
			logger.info("Main window closed.")
			self.ended.set()
		
		self.main_widget.connect('destroy', lambda messenger: on_destroy())
	
	async def start(self):
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
				await self.create_xmpp_connection(jid, alt_host, port, legacy_ssl, password, register=False)
		except (ConnectionError, ProtocolError) as error:
			if self.entry_host.get_text():
				entry = self.entry_host
			else:
				entry = self.entry_login_jid			
			entry.grab_focus()
			entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		except AuthenticationError as error:
			self.entry_login_password.grab_focus()
			self.entry_login_password.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
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
		password = self.entry_registration_password_2.get_text()
		
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
				await self.create_xmpp_connection(jid, alt_host, port, legacy_ssl, password, register=True)
		except (ConnectionError, ProtocolError) as error:
			if self.entry_host.get_text():
				entry = self.entry_host
			else:
				entry = self.entry_registration_jid			
			entry.grab_focus()
			entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, self.BROKEN_CONNECTION_ICON)
			entry.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, gettext(str(error)))
			return
		
		self.entry_registration_jid.set_text("")
		self.entry_registration_password_1.set_text("")
		self.entry_registration_password_2.set_text("")
		self.entry_host.set_text("")
		self.entry_port.set_text("")
		self.toggle_legacy_ssl.set_active(False)
	
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
		widget.set_icon_from_icon_name(icon_pos, None) # hide error icon when it's clicked on
	
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
	
	async def show_main_page(self, page_name, key, sidebar_item):
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
		#
		self.stack_main.set_visible_child_name(page_name)
	
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
							
							# <query xmlns="jabber:iq:register"><username/><password/><instructions>Choose a username and password to register with this server</instructions></query>
							
							try:
								form.xpath('xep-0077:username', namespaces=client.namespace)[0].text = jid.split('@')[0]
								form.xpath('xep-0077:password', namespaces=client.namespace)[0].text = password
								if form.xpath('xep-0077:email', namespaces=client.namespace):
									email_form = fromstring(f'<x xmlns="jabber:x:data" type="form"><field type="text-single" label="{gettext("Email address")}" var="email"><required/></field></x>')
									proceed = await self.registration_form(email_form, client)
									form.xpath('xep-0077:email', namespaces=client.namespace)[0].text = email_form.xpath('xep-0004:field[@var="email"]', namespaces=client.namespace)[0].text
								else:
									proceed = True
							except IndexError:
								from base64 import b64decode # TODO
								for medium in form.xpath('xep-0231:data', namespaces=client.namespace):
									#print("set_resource", medium)
									client.set_resource(medium.attrib['cid'], b64decode(medium.text), medium.attrib['type'])
								proceed = await self.registration_form(form.xpath('xep-0004:x', namespaces=client.namespace)[0], client)
							
							if not proceed:
								break
							result = await client.iq_set(jid.split('@')[1].split('/')[0], form)
							register = False
						
						self.xmpp_clients[jid] = client
						await self.add_sidebar_server(jid)
						await self.select_sidebar_item(jid)
						
						try:
							logger.debug("XMPP connection ready.")
							ready.set() # mark login success
							retry = 3
							
							@client.task
							async def message(client):
								while (stanza := await client.expect('self::client:message')) is not None:
									await self.message(client, stanza)
							
							@client.task
							async def presence(client):
								while (stanza := await client.expect('self::client:presence')) is not None:
									await self.presence(client, stanza)
							
							await client.process()
						
						finally:
							await self.remove_sidebar_item(jid)
							del self.xmpp_clients[jid]
				
				except ConnectionError as error:
					logger.error("Connection error in XMPP client: {errror}")
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
		
		if not wait_for_ended.done():
			wait_for_ended.cancel()
			await task # should exit gracefully
		
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
	
	@asynchandler
	async def xmpp_logout(self, widget):
		...
	
	#async def presence(self, client, stanza):
	#	...
	
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
	
	async def add_sidebar_server(self, server_jid):
		"Create sidebar item for the new connection."
		sidebar_item = BuilderExtension(self, ['sidebar_server'], 'sidebar_server')
		sidebar_item.entry_account_jid.set_text(server_jid)
		await self.add_sidebar_item((server_jid,), 'page_server', sidebar_item)
	
	async def add_sidebar_contact(self, server_jid, contact_jid):
		sidebar_item = SidebarContact(self)
		await self.add_sidebar_item((server_jid, contact_jid), 'page_contact', sidebar_item)
		await sidebar_item.domwidget_contact_avatar.open(f'resource://guixmpp/jabber-avatar?account={server_jid}&contact={contact_jid}')
	
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


if __name__ == '__main__':
	from logging import DEBUG, basicConfig
	basicConfig(level=DEBUG)
	logger.setLevel(DEBUG)
	
	logger.info("messenger")
	
	from asyncio import run, get_running_loop
	from locale import bindtextdomain, textdomain
	from guixmpp.domevents import Event as DOMEvent
	
	loop_init()
	translation = 'haael_svg_messenger'
	bindtextdomain(translation, 'locale')
	textdomain(translation)
	
	async def main():
		DOMEvent._time = get_running_loop().time
		async with Messenger('messenger.glade', translation) as messenger:
			await messenger.process()
	
	run(loop_main(main()))

