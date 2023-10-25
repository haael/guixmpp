#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib, GdkPixbuf

from collections import defaultdict, deque
from locale import gettext
from random import randrange
from asyncio import sleep, wait_for, get_running_loop, open_connection


'''

from tinyxmpp import XMPPClient


class Messenger:
	def __init__(self, max_messages, connect_timeout):
		self.max_messages = max_messages
		self.connect_timeout = connect_timeout
		
		self.on_connected = {}
		self.on_disconnected = {}
		self.on_message = {}
		self.on_presence = {}
		self.__clients = {}
		self.__messages = defaultdict(deque)
		self.__presence = {}
	
	def is_logged_in(self, account_jid):
		return account_jid in self.__clients
	
	async def __on_message(self, account_jid, message):
		print(message)
		from_ = message.attrib['from']
		messages = self.__messages[account_jid, from_]
		messages.append(message)
		if len(messages) >= self.max_messages:
			del messages[0]
		if (account_jid, from_) in self.on_message:
			await self.on_message[account_jid, from_](message)
	
	async def __on_presence(self, account_jid, presence):
		print(presence)
		from_ = presence.attrib['from']
		self.__presence[account_jid, from_] = presence
		if (account_jid, from_) in self.on_presence:
			await self.on_presence[account_jid, from_](presence)
	
	async def login(self, account_jid, password):
		client = XMPPClient(account_jid, password)
		client.connect_timeout = self.connect_timeout
		self.__clients[account_jid] = client
		client.on_presence = lambda _presence: self.__on_presence(account_jid, _presence)
		client.on_message = lambda _message: self.__on_message(account_jid, _message)
		try:
			await client.connect(account_jid.split('@')[1].split('/')[0], ssl=False)
		except:
			del self.__clients[account_jid]
			raise
		
		if not (await client.authorized):
			del self.__clients[account_jid]
			raise RuntimeError("Unauthorized")
	
	async def logout(self, account_jid):
		client = self.__clients[account_jid]
		await client.disconnect()
		del self.__clients[account_jid]
	
	async def register(self, account_jid, password):
		raise NotImplementedError
	
	async def unregister(self, account_jid):
		raise NotImplementedError
	
	async def change_password(self, account_jid, password):
		raise NotImplementedError
	
	async def roster(self, account_jid):
		raise NotImplementedError
	
	async def roster_add(self, account_jid, friend_jid):	
		raise NotImplementedError
	
	async def roster_delete(self, account_jid, friend_jid):
		raise NotImplementedError
	
	async def command_list(self, account_jid, service_jid):
		raise NotImplementedError
	
	async def chatroom_list(self, account_jid, service_jid):
		raise NotImplementedError
	
	async def send_message(self, account_jid, friend_jid, message):
		await self.__clients[account_jid].send_message(friend_jid, message)
	
	async def receive_presence(self, account_jid, friend_jid):
		if (account_jid, friend_jid) not in self.on_presence:
			raise ValueError("Register `on_presence` handler in order to receive messages.")
		
		if (account_jid, friend_jid) in self.__presence:
			await self.on_presence[account_jid, friend_jid](self.__presence[account_jid, friend_jid])
	
	async def receive_messages(self, account_jid, friend_jid, max_messages):
		if (account_jid, friend_jid) not in self.on_message:
			raise ValueError("Register `on_message` handler in order to receive messages.")
		on_message = self.on_message[account_jid, friend_jid]
		
		if (account_jid, friend_jid) in self.__messages:
			for message in self.__messages[account_jid, friend_jid][-max_messages:]:
				await on_message(message)
	
	async def http_put(self, account_jid, service_jid, file_stream, file_name, mime_type):
		raise NotImplementedError
	
	async def http_get(self, url, file_stream):
		raise NotImplementedError
	
	def keys(self):
		return self.__clients.keys()
	
	def __getitem__(self, account_jid):
		return Account(self, account_jid)


class Account:
	def __init__(self, messenger, account_jid):
		self.messenger = messenger
		self.account_jid = account_jid
		self.roster = Roster(self)
		#self.commands = Commands(self)
		#self.chatrooms = Chatrooms(self)
	
	def is_logged_in(self):
		return self.messenger.is_logged_in(self.account_jid)
	
	async def login(self, password):
		await self.messenger.login(self.account_jid, password)
	
	async def logout(self):
		await self.messenger.logout(self.account_jid)
	
	async def register(self, password):
		await self.messenger.register(self.account_jid, password)
	
	async def unregister(self):
		await self.messenger.unregister(self.account_jid)
	
	async def change_password(self, password):
		await self.messenger.change_password(self.account_jid, password)
	
	@property
	def on_connected(self):
		try:
			return self.messenger.on_connected[self.account_jid]
		except KeyError:
			raise AttributeError(f"Handler `on_connected` for {self.account_jid} not found.")
	
	@on_connected.setter
	def on_connected(self, handler):
		self.messenger.on_connected[self.account_jid] = handler
	
	@on_connected.deleter
	def on_connected(self):
		try:
			del self.messenger.on_connected[self.account_jid]
		except KeyError:
			raise AttributeError(f"Handler `on_connected` for {self.account_jid} not found.")
	
	@property
	def on_disconnected(self):
		try:
			return self.messenger.on_disconnected[self.account_jid]
		except KeyError:
			raise AttributeError(f"Handler `on_disconnected` for {self.account_jid} not found.")
	
	@on_disconnected.setter
	def on_disconnected(self, handler):
		self.messenger.on_disconnected[self.account_jid] = handler
	
	@on_disconnected.deleter
	def on_disconnected(self):
		try:
			del self.messenger.on_disconnected[self.account_jid]
		except KeyError:
			raise AttributeError(f"Handler `on_disconnected` for {self.account_jid} not found.")


class Roster:
	def __init__(self, account):
		self.account = account
		self.friend_jids = list()
	
	async def retrieve(self):
		self.friend_jids = list(await self.account.messenger.roster(self.account.account_jid))
	
	def keys(self):
		return self.friend_jids
	
	async def add(self, friend_jid):
		await self.account.messenger.roster_add(self.account.account_jid, friend_jid)
		self.friend_jids.append(friend_jid)
	
	def __getitem__(self, friend_jid):
		if friend_jid not in self.friend_jids:
			raise KeyError(f"JID not found in roster: {friend_jid}")
		return Friend(self, friend_jid)


class Friend:
	def __init__(self, roster, friend_jid):
		self.roster = roster
		self.friend_jid = friend_jid
	
	async def delete(self):
		await self.roster.account.messenger.roster_delete(self.roster.account.account_jid, self.friend_jid)
		self.roster.friend_jids.remove(self.friend_jid)
	
	async def send_message(self, text):
		await self.roster.account.messenger.send_message(self.roster.account.account_jid, self.friend_jid, text)
	
	async def receive_presence(self):
		return await self.roster.account.messenger.receive_presence(self.roster.account.account_jid, self.friend_jid)
	
	async def receive_messages(self, max_messages):
		return await self.roster.account.messenger.receive_messages(self.roster.account.account_jid, self.friend_jid, max_messages)
	
	@property
	def on_presence(self):
		try:
			return self.roster.account.messenger.on_presence[self.roster.account.account_jid, self.friend_jid]
		except KeyError:
			raise AttributeError(f"Handler `on_presence` for {self.account_jid} on account {self.roster.account.account_jid} not found.")
	
	@on_presence.setter
	def on_presence(self, handler):
		self.roster.account.messenger.on_presence[self.roster.account.account_jid, self.friend_jid] = handler
	
	@on_presence.deleter
	def on_presence(self):
		try:
			del self.roster.account.messenger.on_presence[self.roster.account.account_jid, self.friend_jid]
		except KeyError:
			raise AttributeError(f"Handler `on_presence` for {self.account_jid} on account {self.roster.account.account_jid} not found.")
	
	@property
	def on_message(self):
		try:
			return self.roster.account.messenger.on_message[self.roster.account.account_jid, self.friend_jid]
		except KeyError:
			raise AttributeError(f"Handler `on_message` for {self.account_jid} on account {self.roster.account.account_jid} not found.")
	
	@on_message.setter
	def on_message(self, handler):
		self.roster.account.messenger.on_message[self.roster.account.account_jid, self.friend_jid] = handler
	
	@on_message.deleter
	def on_message(self):
		try:
			del self.roster.account.messenger.on_message[self.roster.account.account_jid, self.friend_jid]
		except KeyError:
			raise AttributeError(f"Handler `on_message` for {self.account_jid} on account {self.roster.account.account_jid} not found.")



	

if __name__ == '__main__':
	from asyncio import run, new_event_loop
	from logging import getLogger, DEBUG, INFO, basicConfig
	
	basicConfig(level=INFO)
	getLogger('tinyxmpp').setLevel(DEBUG)
	
	async def main():
		messenger = Messenger(1000, 6)
		await messenger.login('haael@dw.live/discovery', 'deepweb.net:12345')
		print("logged in")
		#await messenger.logout('haael@dw.live')
	
	#run(main())
	
	loop = new_event_loop()
	loop.create_task(main())
	loop.run_forever()
























quit()

'''


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
	
	def __getattr__(self, attr):
		widget = self.__builder.get_object(attr)
		if widget != None:
			setattr(self, attr, widget)
			return widget
		else:
			raise AttributeError(gettext("Attribute not found in object nor in builder:") + " " + attr)


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


class ServerIcon(BuilderExtension):
	def __init__(self, interface, translation):
		super().__init__(interface, translation, [], '')
	
	@property
	def caption(self):
		...
	
	@caption.setter
	def caption(self, value):
		...
	
	@property
	def connected(self):
		...
	
	@connected.setter
	def connected(self, value):
		...
	
	def on_connected(self):
		self.connected = True
	
	def on_disconnected(self):
		self.connected = False


class UserIcon(BuilderExtension):
	def __init__(self, interface, translation):
		super().__init__(interface, translation, [], '')
	
	@property
	def name(self):
		...
	
	@property
	def avatar(self):
		...
	
	@property
	def status(self):
		...
	
	@property
	def presence(self):
		...








def network_thread(old_method):
	def new_method(self, *args, **kwargs):
		coro = old_method(self, *args, **kwargs)
		
		if hasattr(coro, '__aiter__'):
			async def anext(coro):
				return await coro.__anext__()
			
			async def iter_coro():
				while True:
					try:
						yield await wrap_future(run_coroutine_threadsafe(anext(coro), self.net_loop))
					except StopAsyncIteration:
						break
			
			return iter_coro()
		
		else:
			return wrap_future(run_coroutine_threadsafe(coro, self.net_loop))
	
	return new_method
	
	#def new_method(self, *args, **kwargs):
	#	return self.ui_loop.run_in_executor(None, lambda: run_coroutine_threadsafe(old_method(self, *args, **kwargs), self.net_loop).result())
	#return new_method


class Browser(BuilderExtension):
	def __init__(self, interface, translation, ui_loop, net_loop):
		super().__init__(interface, translation, ['main_window'], 'main_window')
		
		self.interface = interface
		self.translation = translation
		self.ui_loop = ui_loop
		self.net_loop = net_loop
		
		self.login_jid.connect('key-press-event', self.enter_keypress, False, self.login_on_server)
		self.login_password.connect('key-press-event', self.enter_keypress, False, self.login_on_server)
		self.login_button.connect('clicked', self.handler, lambda widget: self.login_on_server())
		
		self.ibr_button.connect('key-press-event', self.enter_keypress, False, self.register_on_server)
		self.ibr_button.connect('clicked', self.handler, lambda widget: self.register_on_server())
		
		self.roster = ListWrapper(self.roster_listbox)
		self.roster_listbox.connect('row-selected', self.handler, lambda widget, row: self.select_screen(widget, row))
		self.chat = ListWrapper(self.chat_listbox)
		self.main_text.connect('key-press-event', self.enter_keypress, True, self.send_message)
		
		self.roster['start'] = BuilderExtension(self.interface, self.translation, ['roster_start'], 'roster_start')
		self.main_stack.set_visible_child_name('start')
		
		self.services_iconview.set_text_column(0)
		self.services_iconview.set_pixbuf_column(1)
		
		self.xmpp_connections = {}
		self.server_models = {}
		self.tasks = []
		self.running = False
	
	def handler(self, *args):
		print("handler")
		*fargs, callback = args
		
		task = callback(*fargs)
		self.tasks.append(task)
		
		def run_tasks():
			if self.tasks:
				self.ui_loop.run_until_complete(self.tasks.pop())
				return True
			else:
				return False
		
		#def delay_run_tasks():
		#	if not self.ui_loop.is_running():
		#		GLib.idle_add(run_tasks)
		#		return False
		#	else:
		#		return True
		
		if not self.ui_loop.is_running():
			GLib.idle_add(run_tasks)
		#else:
		#	GLib.timeout_add(100, delay_run_tasks)
		
		return True
	
	def enter_keypress(self, widget, event, ignore_shift, callback, *args):
		if Gdk.keyval_name(event.keyval) == 'Return' and ((not (event.state & Gdk.ModifierType.SHIFT_MASK)) if ignore_shift else True):
			self.handler(*args, callback)
			return True
		return False
	
	def run_later(self, callback, *args):
		def handler_later():
			self.handler(*args, callback)
			return False
		GLib.idle_add(handler_later)
	
	async def select_screen(self, listbox, row):
		try:
			key = self.roster.index(row.get_child())
		except IndexError:
			return
		
		if key == 'start':
			self.main_stack.set_visible_child_name('start')
		elif key.startswith('server '):
			self.services_iconview.set_model(self.server_models[key])
			self.main_stack.set_visible_child_name('server')
		elif key.startswith('muc '):
			self.chat.clear()
			self.main_stack.set_visible_child_name('chat')
		elif key.startswith('app '):
			self.main_stack.set_visible_child_name('app')
		else:
			self.chat.clear()
			self.main_stack.set_visible_child_name('chat')
	
	async def startup(self):
		print("startup")
		
		'''
		profile = BuilderExtension(self.interface, self.translation, ['roster_item'], 'roster_item')
		profile.profile_username.set_text("Zbączysław Dobuzibierski Marszczyciel Naczelny")
		profile.profile_status_text.set_text("This is status pójdź kińże tę chmurność w głąb flaszy pójdź kińże tę chmurność w głąb flaszy pójdź kińże tę chmurność w głąb flaszy pójdź kińże tę chmurność w głąb flaszy pójdź kińże tę chmurność w głąb flaszy pójdź kińże tę chmurność w głąb flaszy")
		self.roster['one@haael.net'] = profile
		
		profile = BuilderExtension(self.interface, self.translation, ['roster_item'], 'roster_item')
		profile.profile_username.set_text("Maluch Paluch")
		profile.profile_status_text.set_text("lskadj ldkfgj ,rmtn ldkjf lkjg lkvjvd rwth tyjtyjt sdfsdf sghsghs")
		self.roster['two@haael.net'] = profile
		
		self.chat[randrange(0, 1000000)] = BuilderExtension(self.interface, self.translation, ['message_loading'], 'message_loading')
		
		self.receive_message("skdjfh kjhkjh erj jktr fkhicu weiuriew fjhgerj uqwff sdmbsp bbsjdf")
		self.receive_message("dbfm, wet xerge eheth dzbz rthrt zerwe lkuylky sdg")
		'''
		pass
	
	async def cleanup(self):
		print("cleanup")
		for client in self.xmpp_connections.values():
			client.stop()
		pass
	
	async def register_on_server(self):
		addr = self.ibr_server.get_text().strip()
		if not addr:
			self.ibr_server.grab_focus()
			self.ibr_view.hide()
			return
		self.ibr_view.show()
	
	@network_thread
	async def xmpp_connect(self, jid, pwd):
		bad_pwd = bad_jid = False
		client = None
		try:
			print("connecting client")
			future = Future()
			client = aioxmpp.PresenceManagedClient(aioxmpp.JID.fromstr(jid), aioxmpp.make_security_layer(pwd))
			client.on_stream_established.connect(future, client.on_stream_established.AUTO_FUTURE)
			client.on_failure.connect(future, client.on_failure.AUTO_FUTURE)
			client.start()
			await future
		except aiosasl.common.AuthenticationFailure:
			print("bad password")
			bad_pwd = True
		except aioxmpp.errors.MultiOSError:
			print("connection error")
			bad_jid = True
		except:
			raise
		
		if not bad_pwd and not bad_jid:
			assert client.running
		
		return client, bad_pwd, bad_jid
	
	@network_thread
	async def xmpp_service_discovery(self, client, jid):
		jid = aioxmpp.JID.fromstr(jid)
		disco = aioxmpp.DiscoClient(client)
		
		async def service_discovery(jid, level):
			info = await disco.query_info(jid)
			yield level, jid, info
			#features = frozenset(_feature for _feature in info.features)
			if 'http://jabber.org/protocol/disco#items' in info.features:
				items = await disco.query_items(jid)
				for item in items.items:
					if str(item.jid).endswith(str(jid)):
						async for subnode in service_discovery(item.jid, level + 1):
							yield subnode
					else:
						try:
							info = await disco.query_info(item.jid)
						except aioxmpp.errors.XMPPWaitError:
							pass
						else:
							yield level + 1, item.jid, info
		
		async for items in service_discovery(jid, 0):
			yield items
	
	async def login_on_server(self):
		print("login on server")
		
		jid = self.login_jid.get_text().strip()
		if not jid:
			self.login_jid.grab_focus()
			return
		
		pwd = self.login_password.get_text()
		if not pwd:
			self.login_password.grab_focus()
			return
		
		if jid in self.xmpp_connections:
			print("already connected")
			return
		
		self.login_button.props.sensitive = False
		self.login_jid.props.sensitive = False
		self.login_password.props.sensitive = False
				
		client, bad_pwd, bad_jid = await self.xmpp_connect(jid, pwd)
		
		self.login_button.props.sensitive = True
		self.login_jid.props.sensitive = True
		self.login_password.props.sensitive = True
		if bad_pwd: self.login_password.grab_focus()
		if bad_jid: self.login_jid.grab_focus()
		
		if bad_pwd or bad_jid: return
		
		self.login_jid.set_text("")
		self.login_password.set_text("")
		
		self.xmpp_connections[jid] = client
		
		widget = BuilderExtension(self.interface, self.translation, ['roster_server'], 'roster_server')
		widget.roster_server_name.set_text(jid)
		wid = f'server {jid}'
		self.roster[wid] = widget
		self.roster.select(wid)
		model = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
		self.server_models[wid] = model
		self.services_iconview.set_model(model)
		
		self.run_later(self.populate_services, jid, model)
	
	async def populate_services(self, jid, model):
		model.clear()
		client = self.xmpp_connections[jid]
		async for level, sjid, info in self.xmpp_service_discovery(client, jid.split('@')[1]):
			name = category = None
			if info:
				try:
					category, name = [(_iden.category, _iden.name) for _iden in info.identities][0]
				except IndexError:
					pass
			
			if not name:
				name = str(sjid)
			
			#print(" " * level, sjid, category, repr(name))
			model.append((name, None))
	
	async def send_message(self):
		widget = BuilderExtension(self.interface, self.translation, ['message_right'], 'message_right')
		widget.message_right_time.set_text("00:00")
		widget.message_right_name.hide()
		buffer = self.main_text.get_buffer()
		widget.message_right_content.get_buffer().set_text(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False))
		buffer.set_text("")
		self.chat[randrange(0, 1000000)] = widget
	
	async def receive_message(self, message):
		widget = BuilderExtension(self.interface, self.translation, ['message_left'], 'message_left')
		widget.message_left_time.set_text("00:00")
		widget.message_left_name.set_text("Zboczysław")
		widget.message_left_content.get_buffer().set_text(message)
		self.chat[randrange(0, 1000000)] = widget


if __name__ == '__main__':
	import sys, signal
	from asyncio import set_event_loop_policy, new_event_loop, sleep
	from asyncio_glib import GLibEventLoop
	from locale import bindtextdomain, textdomain
	from threading import Thread
	
	#set_event_loop_policy(GLibEventLoopPolicy())
	
	glib_loop = GLib.MainLoop()
	ui_loop = GLibEventLoop()
	
	net_loop = None
	def net_run():
		print("net thread start")
		global net_loop
		net_loop = new_event_loop()
		run_coroutine_threadsafe(sleep(0), ui_loop)
		net_loop.run_forever()
		print("net thread end")
	
	net_thread = Thread(target=net_run)
	net_thread.start()
	ui_loop.run_until_complete(sleep(0.1))
	
	translation = 'haael_svg_browser'
	bindtextdomain(translation, 'locale')
	textdomain(translation)	
	
	browser = Browser('main.glade', translation, ui_loop, net_loop)
	ui_loop.run_until_complete(browser.startup())
	
	browser.main_widget.connect('destroy', lambda window: glib_loop.quit())
	signal.signal(signal.SIGTERM, lambda signum, frame: glib_loop.quit())
	
	browser.main_widget.show()
	
	try:
		glib_loop.run()
	except KeyboardInterrupt:
		print()
	
	ui_loop.run_until_complete(browser.cleanup())
	
	async def net_stop():
		net_loop.stop()
	run_coroutine_threadsafe(net_stop(), net_loop)
	net_thread.join()
	net_loop.close()
	
	ui_loop.close()
