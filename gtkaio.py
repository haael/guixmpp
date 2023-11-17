#!/usr/bin/python3


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from asyncio.events import *
from asyncio import Future, Task, iscoroutine
from asyncio.tasks import current_task

from math import floor


class GtkAioHandle(Handle):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.source_id = None
	
	def cancel(self):
		if self.source_id is not None:
			GLib.Source.remove(self.source_id)
			self.source_id = None
		super().cancel()
	
	def cancelled(self):
		return super().cancelled() or (self.source_id is None)


class GtkAioEventLoop(AbstractEventLoop):
	def __init__(self):
		self.closed = False
		self.task_factory = None
		self.debug_flag = False
		self.exception_handler = None
		self.completing = None
		self.signal = {}
	
	def run_forever(self):
		"""Run the event loop until stop() is called."""
		
		if self.is_running() or self.is_closed():
			raise RuntimeError
		
		_set_running_loop(self)
		Gtk.main()
		_set_running_loop(None)
	
	def _check_completing_state(self):
		if self.completing is not None and self.completing.done():
			Gtk.main_quit()
		return False
	
	def run_until_complete(self, future):
		"""Run the event loop until a Future is done.
		Return the Future's result, or raise its exception.
		"""
		
		if self.is_running() or self.is_closed():
			raise RuntimeError
		
		if iscoroutine(future):
			future = self.create_task(future)
		
		self.completing = future
		_set_running_loop(self)
		GLib.idle_add(self._check_completing_state)
		Gtk.main()
		result = self.completing.result()
		_set_running_loop(None)
		self.completing = None
		return result
	
	def stop(self):
		"""Stop the event loop as soon as reasonable.
		Exactly how soon that is may depend on the implementation, but
		no more I/O callbacks should be scheduled.
		"""
		
		if not self.is_running() or self.is_closed():
			raise RuntimeError
		
		Gtk.main_quit()
	
	def is_running(self):
		"""Return whether the event loop is currently running."""
		return Gtk.main_level() > 0
	
	def is_closed(self):
		"""Returns True if the event loop was closed."""
		return self.closed
	
	def close(self):
		"""Close the loop.
		The loop should not be running.
		This is idempotent and irreversible.
		No other methods should be called after this one.
		"""
		if self.is_running():
			raise RuntimeError
		self.closed = True
	
	async def shutdown_asyncgens(self):
		"""Shutdown all active asynchronous generators."""
		pass # TODO
	
	async def shutdown_default_executor(self):
		pass # TODO
	
	# Methods scheduling callbacks.  All these return Handles.
	
	def _timer_handle_cancelled(self, handle):
		"""Notification that a TimerHandle has been cancelled."""
		raise NotImplementedError
	
	def call_soon(self, callback, *args, context=None):
		def _call_soon(handle, *args):
			if current_task() is not None: # another task is running, postpone call
				return True
			callback(*args)
			handle.source_id = None
			self._check_completing_state()
			return False
		
		handle = GtkAioHandle(callback, args, self, context)
		handle.source_id = GLib.idle_add(_call_soon, handle, *args)
		return handle
	
	def call_later(self, delay, callback, *args, context=None):
		def _call_later(handle, *args):
			callback(*args)
			handle.source_id = None
			self._check_completing_state()
			return False
		
		handle = GtkAioHandle(callback, args, self, context)
		handle.source_id = GLib.timeout_add(floor(delay * 1000), _call_later, handle, *args)
		return handle
	
	def call_at(self, when, callback, *args, context=None):
		return self.call_later(when - self.time(), callback, *args, context=context)
	
	def time(self):
		return GLib.get_monotonic_time() / 10**6
	
	def create_future(self):
		return Future(loop=self)
	
	# Method scheduling a coroutine object: create a task.
	
	def create_task(self, coro, *, name=None, context=None):
		if self.task_factory is None:
			return Task(coro, loop=self, name=name, context=context)
		else:
			task = self.task_factory(self, coro, context)
			if name:
				task.set_name(name)
			return task

	# Methods for interacting with threads.

	#def call_soon_threadsafe(self, callback, *args):
	#	raise NotImplementedError
	call_soon_threadsafe = call_soon

	def run_in_executor(self, executor, func, *args):
		raise NotImplementedError

	def set_default_executor(self, executor):
		raise NotImplementedError

	# Network I/O methods returning Futures.

	def getaddrinfo(self, host, port, *, family=0, type=0, proto=0, flags=0):
		raise NotImplementedError

	def getnameinfo(self, sockaddr, flags=0):
		raise NotImplementedError

	def create_connection(self, protocol_factory, host=None, port=None, *,
						  ssl=None, family=0, proto=0, flags=0, sock=None,
						  local_addr=None, server_hostname=None):
		raise NotImplementedError

	'''
	def create_server(self, protocol_factory, host=None, port=None, *,
					  family=socket.AF_UNSPEC, flags=socket.AI_PASSIVE,
					  sock=None, backlog=100, ssl=None, reuse_address=None,
					  reuse_port=None):
		"""A coroutine which creates a TCP server bound to host and port.

		The return value is a Server object which can be used to stop
		the service.

		If host is an empty string or None all interfaces are assumed
		and a list of multiple sockets will be returned (most likely
		one for IPv4 and another one for IPv6). The host parameter can also be a
		sequence (e.g. list) of hosts to bind to.

		family can be set to either AF_INET or AF_INET6 to force the
		socket to use IPv4 or IPv6. If not set it will be determined
		from host (defaults to AF_UNSPEC).

		flags is a bitmask for getaddrinfo().

		sock can optionally be specified in order to use a preexisting
		socket object.

		backlog is the maximum number of queued connections passed to
		listen() (defaults to 100).

		ssl can be set to an SSLContext to enable SSL over the
		accepted connections.

		reuse_address tells the kernel to reuse a local socket in
		TIME_WAIT state, without waiting for its natural timeout to
		expire. If not specified will automatically be set to True on
		UNIX.

		reuse_port tells the kernel to allow this endpoint to be bound to
		the same port as other existing endpoints are bound to, so long as
		they all set this flag when being created. This option is not
		supported on Windows.
		"""
		raise NotImplementedError
	'''

	def create_unix_connection(self, protocol_factory, path, *,
							   ssl=None, sock=None,
							   server_hostname=None):
		raise NotImplementedError

	def create_unix_server(self, protocol_factory, path, *,
						   sock=None, backlog=100, ssl=None):
		"""A coroutine which creates a UNIX Domain Socket server.

		The return value is a Server object, which can be used to stop
		the service.

		path is a str, representing a file systsem path to bind the
		server socket to.

		sock can optionally be specified in order to use a preexisting
		socket object.

		backlog is the maximum number of queued connections passed to
		listen() (defaults to 100).

		ssl can be set to an SSLContext to enable SSL over the
		accepted connections.
		"""
		raise NotImplementedError

	def create_datagram_endpoint(self, protocol_factory,
								 local_addr=None, remote_addr=None, *,
								 family=0, proto=0, flags=0,
								 reuse_address=None, reuse_port=None,
								 allow_broadcast=None, sock=None):
		"""A coroutine which creates a datagram endpoint.

		This method will try to establish the endpoint in the background.
		When successful, the coroutine returns a (transport, protocol) pair.

		protocol_factory must be a callable returning a protocol instance.

		socket family AF_INET or socket.AF_INET6 depending on host (or
		family if specified), socket type SOCK_DGRAM.

		reuse_address tells the kernel to reuse a local socket in
		TIME_WAIT state, without waiting for its natural timeout to
		expire. If not specified it will automatically be set to True on
		UNIX.

		reuse_port tells the kernel to allow this endpoint to be bound to
		the same port as other existing endpoints are bound to, so long as
		they all set this flag when being created. This option is not
		supported on Windows and some UNIX's. If the
		:py:data:`~socket.SO_REUSEPORT` constant is not defined then this
		capability is unsupported.

		allow_broadcast tells the kernel to allow this endpoint to send
		messages to the broadcast address.

		sock can optionally be specified in order to use a preexisting
		socket object.
		"""
		raise NotImplementedError

	# Pipes and subprocesses.

	def connect_read_pipe(self, protocol_factory, pipe):
		"""Register read pipe in event loop. Set the pipe to non-blocking mode.

		protocol_factory should instantiate object with Protocol interface.
		pipe is a file-like object.
		Return pair (transport, protocol), where transport supports the
		ReadTransport interface."""
		# The reason to accept file-like object instead of just file descriptor
		# is: we need to own pipe and close it at transport finishing
		# Can got complicated errors if pass f.fileno(),
		# close fd in pipe transport then close f and vise versa.
		raise NotImplementedError

	def connect_write_pipe(self, protocol_factory, pipe):
		"""Register write pipe in event loop.

		protocol_factory should instantiate object with BaseProtocol interface.
		Pipe is file-like object already switched to nonblocking.
		Return pair (transport, protocol), where transport support
		WriteTransport interface."""
		# The reason to accept file-like object instead of just file descriptor
		# is: we need to own pipe and close it at transport finishing
		# Can got complicated errors if pass f.fileno(),
		# close fd in pipe transport then close f and vise versa.
		raise NotImplementedError

	'''
	def subprocess_shell(self, protocol_factory, cmd, *, stdin=subprocess.PIPE,
						 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
						 **kwargs):
		raise NotImplementedError

	def subprocess_exec(self, protocol_factory, *args, stdin=subprocess.PIPE,
						stdout=subprocess.PIPE, stderr=subprocess.PIPE,
						**kwargs):
		raise NotImplementedError
	'''

	# Ready-based callback registration methods.
	# The add_*() methods return None.
	# The remove_*() methods return True if something was removed,
	# False if there was nothing to delete.

	def add_reader(self, fd, callback, *args):
		raise NotImplementedError

	def remove_reader(self, fd):
		raise NotImplementedError

	def add_writer(self, fd, callback, *args):
		raise NotImplementedError

	def remove_writer(self, fd):
		raise NotImplementedError

	# Completion based I/O methods returning Futures.

	def sock_recv(self, sock, nbytes):
		raise NotImplementedError

	def sock_sendall(self, sock, data):
		raise NotImplementedError

	def sock_connect(self, sock, address):
		raise NotImplementedError

	def sock_accept(self, sock):
		raise NotImplementedError

	# Signal handling.

	def add_signal_handler(self, sig, callback, *args):
		raise NotImplementedError
		self.signals[sig] = GLib.unix_signal_add(sig, callback, *args)
	
	def remove_signal_handler(self, sig):
		raise NotImplementedError
		GLib.Source.remove(self.signals[sig])
		self.signals[sig] = None

	# Task factory.

	def set_task_factory(self, factory):
		self.task_factory = factory
	
	def get_task_factory(self):
		return self.task_factory

	# Error handlers.

	def get_exception_handler(self):
		return self.exception_handler
	
	def set_exception_handler(self, handler):
		self.exception_handler = handler
	
	def default_exception_handler(self, context):
		print(context)
	
	def call_exception_handler(self, context):
		if self.exception_handler is not None:
			self.exception_handler(self, context)
		else:
			self.default_exception_handler(context)
	
	# Debug flag management.

	def get_debug(self):
		return self.debug_flag

	def set_debug(self, enabled):
		self.debug_flag = enabled



class GtkAioEventLoopPolicy(AbstractEventLoopPolicy):
	#def __getattribute__(self, attr):
	#	print("EventLoopPolicy.getattr", attr)
	#	return super().__getattribute__(attr)

	def __init__(self):
		self.loop = None
	
	def get_event_loop(self):
		"""Get the event loop for the current context.
		Returns an event loop object implementing the AbstractEventLoop interface,
		or raises an exception in case no event loop has been set for the
		current context and the current policy does not specify to create one.
		It should never return None."""
		
		if self.loop is None:
			raise RuntimeError
		return self.loop

	def set_event_loop(self, loop):
		"""Set the event loop for the current context to loop."""
		self.loop = loop

	def new_event_loop(self):
		"""Create and return a new event loop object according to this
		policy's rules. If there's need to set this loop as the event loop for
		the current context, set_event_loop must be called explicitly."""
		return GtkAioEventLoop()

	# Child processes handling (Unix only).

	def get_child_watcher(self):
		"Get the watcher for child processes."
		raise NotImplementedError

	def set_child_watcher(self, watcher):
		"""Set the watcher for child processes."""
		raise NotImplementedError



if __debug__ and __name__ == '__main__':
	from asyncio import sleep, set_event_loop_policy, run, gather, create_task
	
	set_event_loop_policy(GtkAioEventLoopPolicy())
	
	async def testA():
		print("testA", 0)
		await sleep(1)
		print("testA", 1)
		print("testA", 2)
		await sleep(1)
		print("testA", 3)
		a = await gather(testB(), testC())
		print("testA", 4, a)
		e = create_task(testE())
		print("testA", 5)
		await sleep(0.2)
		print("testA", 6)
		await sleep(0.2)
		print("testA", 7)
		await sleep(0.2)
		await e
		#return "a", a
		return "a", a
	
	async def testB():
		print("testB", 0)
		await sleep(1)
		print("testB", 1)
		async for k in testD():
			await sleep(0.1)
			print(k)
		return "b"
	
	async def testC():
		for n in range(3):
			print("testC", n)
			await sleep(1)
		return "c"
	
	async def testD():
		for n in range(4):
			await sleep(0.4)
			yield f"d{n}"

	async def testE():
		for n in range(10):
			await sleep(0.3)
			print("testE", n)
	
	a = run(testA())
	print("a=", a)
