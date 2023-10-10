#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib

from locale import gettext
from random import randrange
from asyncio import run, get_running_loop

import aioxmpp
import aioxmpp.ibr
import aioxmpp.errors
import aiosasl.common

import asyncio
from asyncio import run_coroutine_threadsafe


class BuilderExtension:
	def __init__(self, interface, translation, objects, main_widget_name):
		#self.interface = interface
		#self.translation = translation
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


class ListWrapper:
	def __init__(self, listbox):
		self.__listbox = listbox
		self.__items = {}
	
	def index(self, item):
		return [_key for (_key, _value) in self.__items.items() if _value.main_widget is item][0]
	
	def clear(self):
		for child in self.__listbox.get_children():
			self.__listbox.remove(child)
		self.__items.clear()
	
	def select(self, name):
		item = self.__items[name].main_widget
		child = [_child for _child in self.__listbox.get_children() if _child.get_child() is item][0]
		self.__listbox.select_row(child)
	
	def __getitem__(self, name):
		return self.__items[name]
	
	def __setitem__(self, name, item):
		self.__listbox.add(item.main_widget)
		self.__items[name] = item
		return item
	
	def __delitem__(self, name):
		item = self.__items[name].main_widget
		child = [_child for _child in self.__listbox.get_children() if _child.get_child() is item][0]
		self.__listbox.remove(child)
		del self.__items[name]


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
		
		self.xmpp_connections = {}
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
		
		GLib.idle_add(run_tasks)
		return True
	
	def enter_keypress(self, widget, event, ignore_shift, callback, *args):
		if Gdk.keyval_name(event.keyval) == 'Return' and ((not (event.state & Gdk.ModifierType.SHIFT_MASK)) if ignore_shift else True):
			self.handler(*args, callback)
			return True
		return False
	
	async def select_screen(self, listbox, row):
		try:
			key = self.roster.index(row.get_child())
		except IndexError:
			return
		
		if key == 'start':
			self.main_stack.set_visible_child_name('start')
		elif key.startswith('server '):
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
		
		bad_pwd = bad_jid = False
		client = None
		
		async def connect():
			nonlocal bad_pwd, bad_jid, client
			try:
				print("connecting client")
				client = aioxmpp.PresenceManagedClient(aioxmpp.JID.fromstr(jid), aioxmpp.make_security_layer(pwd))
				async with client.connected():
					print("connected")
			except aiosasl.common.AuthenticationFailure:
				print("bad password")
				client.stop()
				bad_pwd = True
			except aioxmpp.errors.MultiOSError:
				print("connection error")
				client.stop()
				bad_jid = True
			except:
				client.stop()
				raise
		
		await self.ui_loop.run_in_executor(None, lambda: run_coroutine_threadsafe(connect(), self.net_loop).result())
		
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
