#!/usr/bin/python3


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio

import asyncio.events
import asyncio.transports

from asyncio import Future, Task, iscoroutine, gather
from asyncio.tasks import current_task
from asyncio.events import _set_running_loop

import socket
import ssl
from math import floor
from collections import deque

from protocol.dns import AsyncResolver


class Handle(asyncio.events.Handle):
	def __init__(self, callback, args, loop, *, context=None):
		super().__init__(callback, args, loop, context=context)
		self.__source = GLib.idle_add(self.__callback)
	
	def __callback(self):
		if current_task() is not None: # another task is running, postpone call
			return True
		self._run()
		self.__source = None
		self._loop._check_completing_state()
		return False
	
	def cancel(self):
		if self.__source is not None:
			GLib.Source.remove(self.__source)
			self.__source = None
		super().cancel()
	
	def cancelled(self):
		return super().cancelled() or (self.__source is None)


class TimerHandle(asyncio.events.TimerHandle):
	def __init__(self, when, callback, args, loop, *, context=None, current_time=None):
		super().__init__(when, callback, args, loop, context=context)
		if current_time is None:
			current_time = loop.time()
		self.__source = GLib.timeout_add(((when - current_time) * 1000), self.__callback)
	
	def __callback(self):
		#if current_task() is not None: # another task is running, postpone call
		#	return True
		self._run()
		self.__source = None
		self._loop._check_completing_state()
		return False
	
	def cancel(self):
		if self.__source is not None:
			GLib.Source.remove(self.__source)
			self.__source = None
		super().cancel()
	
	def cancelled(self):
		return super().cancelled() or (self.__source is None)


class BaseTransport(asyncio.transports.BaseTransport):
	def __init__(self, endpoint, channel):
		self.__endpoint = endpoint
		self.__channel = channel
		self.__watch_in = None
		self.__watch_out = None		
		self.__protocol = None
	
	def __del__(self):
		self.watch_in(False)
		self.watch_out(False)
	
	def watching_in(self):
		return self.__watch_in is not None
	
	def watch_in(self, watch_in):
		if watch_in and (self.__watch_in is None):
			self.__watch_in = GLib.io_add_watch(self.__channel, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self.__event_in)
		elif (not watch_in) and (self.__watch_in is not None):
			GLib.Source.remove(self.__watch_in)
			self.__watch_in = None
	
	def watching_out(self):
		return self.__watch_out is not None
	
	def watch_out(self, watch_out):
		if watch_out and (self.__watch_out is None):
			self.__watch_out = GLib.io_add_watch(self.__channel, GLib.IO_OUT, self.__event_out)
		elif (not watch_out) and (self.__watch_out is not None):
			GLib.Source.remove(self.__watch_out)
			self.__watch_out = None
	
	def _data_in(self, channel):
		raise NotImplementedError
	
	def _data_out(self, channel):
		raise NotImplementedError
	
	@staticmethod
	def _ret_false(old_fun):
		def new_fun(*args):
			old_fun(*args)
			return False
		new_fun.__name__ = old_fun.__name__
		return new_fun
	
	def __event_out(self, channel, condition):
		if condition & GLib.IO_OUT:
			result = self._data_out(channel)
			if not result:
				self.__watch_out = None
			return result
	
	def __event_in(self, channel, condition):
		if condition & GLib.IO_IN:
			result = self._data_in(channel)
			#print('data_in', result)
		else:
			result = True
		
		if condition & GLib.IO_ERR:
			if self.__protocol:
				GLib.idle_add(self._ret_false(self.__protocol.error_received), None)
			#print('err')
		
		if condition & GLib.IO_HUP:
			if self.__protocol and hasattr(self.__protocol, 'eof_received'):
				GLib.idle_add(self._ret_false(self.__protocol.eof_received))
			result = False
			#print('hup', result)
		
		if result is True:
			return True
		elif result is False:
			if self.__protocol:
				GLib.idle_add(self._ret_false(self.__protocol.connection_lost), None)
				self.__protocol = None
			self.__watch_in = None
			return False
		elif result is None:
			self.__watch_in = None
			return False
		else:
			raise ValueError
	
	def abort(self):
		"""Close the transport immediately.
		
		Buffered data will be lost.  No more data will be received.
		The protocol's connection_lost() method will (eventually) be
		called with None as its argument.
		"""
		
		self.watch_in(False)
		self.watch_out(False)
		
		if self.__channel is not None:
			self.__channel.shutdown(False)
			self.__channel = None
		
		self.close()
	
	def close(self):
		if self.__channel is not None:
			self.__channel.shutdown(True)
			self.__channel = None
		
		if self.__endpoint is not None:
			try:
				self.__endpoint.close()
			except OSError: # might have been closed by `channel.shutdown()`
				pass
			self.__endpoint = None
		
		self.watch_in(False)
		self.watch_out(False)
		
		if self.__protocol is not None:
			GLib.idle_add(self._ret_false(self.__protocol.connection_lost), None)
			self.__protocol = None
	
	def is_closing(self):
		return self.__endpoint is None
	
	def get_extra_info(self, name, default=None):
		try:
			match name:
				case 'peername': # the remote address to which the socket is connected, result of socket.socket.getpeername() (None on error)
					try:
						return self.__endpoint.getpeername()
					except AttributeError:
						raise
					except:
						return None
				
				case 'socket': # socket.socket instance
					return self.__endpoint
				
				case 'sockname': # the socket’s own address, result of socket.socket.getsockname()
					return self.__endpoint.getsockname()
				
				case 'compression': # the compression algorithm being used as a string, or None if the connection isn’t compressed; result of ssl.SSLSocket.compression()
					return self.__endpoint.compression()
				
				case 'cipher': # a three-value tuple containing the name of the cipher being used, the version of the SSL protocol that defines its use, and the number of secret bits being used; result of ssl.SSLSocket.cipher()
					return default
				
				case 'peercert': # peer certificate; result of ssl.SSLSocket.getpeercert()
					return self.__endpoint.getpeercert()
				
				case 'sslcontext': # ssl.SSLContext instance
					return default
				
				case 'ssl_object': # ssl.SSLObject or ssl.SSLSocket instance
					return self.__endpoint
				
				case 'pipe': # pipe object
					return self.__endpoint
				
				case 'subprocess': # subprocess.Popen instance
					return self.__endpoint
				
				case 'iochannel':
					return self.__channel
				
				case 'read_endpoint':
					return self.__endpoint
				
				case 'write_endpoint':
					return self.__endpoint
				
				case _:
					return default
		
		except AttributeError:
			return default
	
	def get_protocol(self):
		return self.__protocol
	
	def set_protocol(self, protocol):
		self.__protocol = protocol
	

class NetworkTransport(BaseTransport):
	def __init__(self, gfamily, gstype, gproto, sock, flags):
		if sock is None:
			if gfamily == Gio.SocketFamily.IPV4:
				family = socket.AF_INET
			elif gfamily == Gio.SocketFamily.IPV6:
				family = socket.AF_INET6
			else:
				raise ValueError
			
			if gproto == Gio.SocketProtocol.UDP:
				proto = socket.IPPROTO_UDP
			elif gproto == Gio.SocketProtocol.TCP:
				proto = socket.IPPROTO_TCP
			else:
				raise ValueError
			
			if gstype == Gio.SocketType.DATAGRAM:
				stype = socket.SOCK_DGRAM
			elif gstype == Gio.SocketType.STREAM:
				stype = socket.SOCK_STREAM
			else:
				raise ValueError
			
			sock = socket.socket(family, stype, proto)
		
		sock.setblocking(False)
		channel = GLib.IOChannel.unix_new(sock.fileno())
		channel.set_encoding(None)
		BaseTransport.__init__(self, sock, channel)
	
	def _data_out(self, channel):
		if hasattr(self, '_NetworkTransport__established'):
			sock = self.get_extra_info('socket')
			errno = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
			if not errno:
				self.__established.set_result(None)
			else:
				self.__established.set_exception(OSError("Error establishing connection", errno))
			return False
	
	def bind(self, glocal_addr, reuse_addr):
		sock = self.get_extra_info('socket')
		if not sock:
			raise ValueError
		
		local_addr = (glocal_addr.get_address().to_string(), glocal_addr.get_port())
		sock.bind(local_addr, reuse_addr)
	
	async def connect(self, loop, gremote_addr):
		sock = self.get_extra_info('socket')
		if not sock:
			raise ValueError
		
		remote_addr = (gremote_addr.get_address().to_string(), gremote_addr.get_port())
		
		try:
			sock.connect(remote_addr)
		except BlockingIOError:
			self.__established = loop.create_future()
			self.watch_out(True)
			await self.__established
			del self.__established
	
	def start(self):
		protocol = self.get_protocol()
		if protocol is not None:
			protocol.connection_made(self)
		
		self.watch_in(True)


class UDPTransport(NetworkTransport, asyncio.transports.DatagramTransport):
	def __init__(self, gfamily, gproto, sock, flags):
		super().__init__(gfamily, Gio.SocketType.DATAGRAM, gproto, sock, flags)
	
	def _data_in(self, channel):
		sock = self.get_extra_info('read_endpoint')
		if not sock:
			return False
		
		protocol = self.get_protocol()
		
		while True:
			try:
				data, addr = sock.recvfrom(4096)
			except BlockingIOError:
				break
			except Exception as error:
				if protocol is not None:
					GLib.idle_add(self._ret_false(protocol.error_received), error)
			else:
				if protocol is not None:
					GLib.idle_add(self._ret_false(protocol.datagram_received), data, addr)
		
		return True
	
	def sendto(self, data, addr=None):
		sock = self.get_extra_info('write_endpoint')
		
		try:
			if addr:
				return sock.sendto(data, addr)
			else:
				return sock.send(data)
		except BlockingIOError:
			raise RuntimeError("Implement proper blocking support")
		except Exception as error:
			protocol = self.get_protocol()
			if protocol is not None:
				GLib.idle_add(self._ret_false(protocol.error_received), error)


class ReadTransport(BaseTransport, asyncio.transports.ReadTransport):
	def __init__(self):
		pass
	
	def _data_in(self, channel):
		sock = self.get_extra_info('read_endpoint')
		if not sock:
			#print('not sock')
			return False
		
		protocol = self.get_protocol()
		if protocol is None:
			#print('protocol is None')
			return False
		
		while True:
			try:
				data = sock.recv(4096)
				assert len(data) != 0
			except (BlockingIOError, ssl.SSLWantReadError):
				break
			GLib.idle_add(self._ret_false(protocol.data_received), data)
		
		return True
	
	def is_reading(self):
		"""Return True if the transport is receiving."""
		return self.watching_in()
	
	def pause_reading(self):
		"""Pause the receiving end.

		No data will be passed to the protocol's data_received()
		method until resume_reading() is called.
		"""
		self.watch_in(False)
	
	def resume_reading(self):
		"""Resume the receiving end.

		Data received will once again be passed to the protocol's
		data_received() method.
		"""
		self.watch_in(True)


class WriteTransport(BaseTransport, asyncio.transports.WriteTransport):
	def __init__(self):
		self.__write_high = 4096
		self.__write_low = 4096
		self.__write_buffer = deque()
		self.__writing = True
	
	def _data_out(self, channel):
		sock = self.get_extra_info('write_endpoint')
		if not sock:
			return False
		
		protocol = self.get_protocol()
		if protocol is None:
			return False
		
		while self.__write_buffer:
			data = self.__write_buffer.popleft()
			l = sock.send(data)
			if l < len(data):
				self.__write_buffer.insert(0, data[l:])
				break
		
		if not self.__writing:
			if self.get_write_buffer_size() <= self.__write_low:
				self.__writing = True
				protocol.resume_writing()
		
		return bool(self.__write_buffer)
	
	def set_write_buffer_limits(self, high=None, low=None):
		"""Set the high- and low-water limits for write flow control.

		These two values control when to call the protocol's
		pause_writing() and resume_writing() methods.  If specified,
		the low-water limit must be less than or equal to the
		high-water limit.  Neither value can be negative.

		The defaults are implementation-specific.  If only the
		high-water limit is given, the low-water limit defaults to an
		implementation-specific value less than or equal to the
		high-water limit.  Setting high to zero forces low to zero as
		well, and causes pause_writing() to be called whenever the
		buffer becomes non-empty.  Setting low to zero causes
		resume_writing() to be called only once the buffer is empty.
		Use of zero for either limit is generally sub-optimal as it
		reduces opportunities for doing I/O and computation
		concurrently.
		"""
		
		if (high is not None) and (low is not None) and high < low:
			raise ValueError("`high` must be greater or equal to `low`.")
		
		if (high is not None and high < 0) or (low is not None and low < 0):
			raise ValueError("`high` and `low` must be greater or equal to 0.")
		
		if high is not None:
			self.__write_high = high
			self.__write_low = min(self.__write_low, high)
		
		if low is not None:
			self.__write_low = low
			self.__write_high = max(self.__write_high, low)
	
	def get_write_buffer_size(self):
		"""Return the current size of the write buffer."""
		return sum(len(_d) for _d in self.__write_buffer)

	def get_write_buffer_limits(self):
		"""Get the high and low watermarks for write flow control.
		Return a tuple (low, high) where low and high are
		positive number of bytes."""
		return self.__write_low, self.__write_high
	
	def write(self, data):
		"""Write some data bytes to the transport.

		This does not block; it buffers the data and arranges for it
		to be sent out asynchronously.
		"""
		
		self.__write_buffer.append(data)
		if self.__writing:
			if self.get_write_buffer_size() > self.__write_high:
				self.__writing = False
				protocol = self.get_protocol()
				if protocol is not None:
					protocol.pause_writing()
		
		self.watch_out(True)
	
	def writelines(self, list_of_data):
		"""Write a list (or any iterable) of data bytes to the transport.

		The default implementation concatenates the arguments and
		calls write() on the result.
		"""
		for data in list_of_data:
			if data:
				self.write(data)
	
	def write_eof(self):
		"""Close the write end after flushing buffered data.

		(This is like typing ^D into a UNIX program reading from stdin.)

		Data may still be received.
		"""
		raise NotImplementedError

	def can_write_eof(self):
		"""Return True if this transport supports write_eof(), False if not."""
		raise NotImplementedError


class TCPTransport(NetworkTransport, ReadTransport, WriteTransport, asyncio.transports.Transport):
	def __init__(self, gfamily, gproto, sock, flags):
		NetworkTransport.__init__(self, gfamily, Gio.SocketType.STREAM, gproto, sock, flags)
		ReadTransport.__init__(self)
		WriteTransport.__init__(self)
	
	def _data_out(self, channel):
		result = NetworkTransport._data_out(self, channel)
		if result in (True, False):
			return result
		
		return WriteTransport._data_out(self, channel)


class SSLTransport(TCPTransport):
	def __init__(self, *args):
		super().__init__(*args)
	
	async def starttls(self, loop, ssl_context, server_hostname):
		sock = self.get_extra_info('socket')
		if not sock:
			return False
		
		sslsock = self.__ssl_socket = ssl_context.wrap_socket(sock, do_handshake_on_connect=False, server_hostname=server_hostname)
		
		while True:
			try:
				sslsock.do_handshake()
				break
			except ssl.SSLWantReadError:
				self.__hands_shaken_in = loop.create_future()
				self.watch_in(True)
				await self.__hands_shaken_in
				del self.__hands_shaken_in
			except ssl.SSLWantWriteError:
				self.__hands_shaken_out = loop.create_future()
				self.watch_out(True)
				await self.__hands_shaken_out
				del self.__hands_shaken_out
	
	def get_extra_info(self, name, default=None):
		match name:
			case 'ssl_object':
				return self.__ssl_socket
				
			case 'read_endpoint':
				return self.__ssl_socket
			
			case 'write_endpoint':
				return self.__ssl_socket
			
			case _:
				return super().get_extra_info(name, default)
	
	def _data_out(self, channel):
		if hasattr(self, '_SSLTransport__hands_shaken_out'):
			self.__hands_shaken_out.set_result(None)
			return None
		else:
			return super()._data_out(channel)
	
	def _data_in(self, channel):
		if hasattr(self, '_SSLTransport__hands_shaken_in'):
			self.__hands_shaken_in.set_result(None)
			return None
		else:
			return super()._data_in(channel)


class GtkAioEventLoop(asyncio.events.AbstractEventLoop):
	def __init__(self):
		self.__closed = False
		self.__task_factory = None
		self.__debug_flag = False
		self.__exception_handler = None
		self.__completing = None
		self.__signal = {}
		self.__resolver = AsyncResolver()
	
	def run_forever(self):
		"""Run the event loop until stop() is called."""
		
		if self.is_running() or self.is_closed():
			raise RuntimeError
		
		_set_running_loop(self)
		
		self.__completing = self.create_task(self.__begin_loop())
		GLib.idle_add(self._check_completing_state)
		Gtk.main()
		result = self.__completing.result()
		self.__completing = None
		
		Gtk.main()
		
		self.__completing = self.create_task(self.__end_loop())
		GLib.idle_add(self._check_completing_state)
		Gtk.main()
		result = self.__completing.result()
		self.__completing = None
		
		_set_running_loop(None)
	
	async def __begin_loop(self):
		await self.__open_resolver()
	
	async def __end_loop(self):
		await self.__close_resolver()
	
	def _check_completing_state(self):
		if self.__completing is not None and self.__completing.done():
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
		
		_set_running_loop(self)
		
		self.__completing = self.create_task(self.__begin_loop())
		GLib.idle_add(self._check_completing_state)
		Gtk.main()
		result = self.__completing.result()
		self.__completing = None
		
		self.__completing = future
		GLib.idle_add(self._check_completing_state)
		Gtk.main()
		result = self.__completing.result()
		self.__completing = None
		
		self.__completing = self.create_task(self.__end_loop())
		GLib.idle_add(self._check_completing_state)
		Gtk.main()
		result = self.__completing.result()
		self.__completing = None
		
		_set_running_loop(None)
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
		return self.__closed
	
	def close(self):
		"""Close the loop.
		The loop should not be running.
		This is idempotent and irreversible.
		No other methods should be called after this one.
		"""
		if self.is_running():
			raise RuntimeError
		self.__closed = True
	
	async def shutdown_asyncgens(self):
		"""Shutdown all active asynchronous generators."""
		pass # TODO
	
	async def shutdown_default_executor(self):
		pass # TODO
	
	# Methods scheduling callbacks.  All these return Handles.
	
	def _timer_handle_cancelled(self, handle):
		"""Notification that a TimerHandle has been cancelled."""
		pass
	
	def call_soon(self, callback, *args, context=None):
		return Handle(callback, args, self, context=context)
	
	def call_later(self, delay, callback, *args, context=None):
		current_time = self.time()
		when = current_time + delay
		return TimerHandle(when, callback, args, self, context=context, current_time=current_time)
	
	def call_at(self, when, callback, *args, context=None):
		return TimerHandle(when, callback, args, self, context=context)
	
	def time(self):
		return GLib.get_monotonic_time() / 10**6
	
	def create_future(self):
		return Future(loop=self)
	
	# Method scheduling a coroutine object: create a task.
	
	def create_task(self, coro, *, name=None, context=None):
		if self.__task_factory is None:
			return Task(coro, loop=self, name=name, context=context)
		else:
			task = self.__task_factory(self, coro, context)
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
	
	async def getaddrinfo(self, host, port, *, family=0, type=0, proto=0, flags=0):
		#print('getaddrinfo', host, port, family, type, proto, flags)
		#print(" AI_PASSIVE", bool(socket.AI_PASSIVE & flags))
		#print(" AI_NUMERICHOST", bool(socket.AI_NUMERICHOST & flags))
		#print(" AI_PASSIVE", bool(socket.AI_PASSIVE | flags))
		
		if family not in [0, socket.AF_UNSPEC, socket.AF_INET, socket.AF_INET6]:
			raise ValueError("Invalid address family.")
		
		info = []
		
		if (socket.AI_PASSIVE & flags) and not host:
			if family == socket.AF_INET:
				info.append((family, type, proto, None, ('', port)))
			elif family == socket.AF_INET6:
				info.append((family, type, proto, None, ('::', port, 0, 0)))
			elif family in [0, socket.AF_UNSPEC]:
				info.append((socket.AF_INET6, type, proto, None, ('::', port, 0, 0)))
				info.append((socket.AF_INET, type, proto, None, ('', port)))
		
		elif socket.AI_NUMERICHOST & flags:
			# TODO: verify host
			
			if family == socket.AF_INET:
				info.append((family, type, proto, None, (host, port)))
			elif family == socket.AF_INET6:
				info.append((family, type, proto, None, (host, port, 0, 0)))
			elif family in [0, socket.AF_UNSPEC]:
				info.append((socket.AF_INET6, type, proto, None, (host, port, 0, 0)))
				info.append((socket.AF_INET, type, proto, None, (host, port)))
		
		else:
			if family == socket.AF_INET:
				for addr4 in await self.__resolver.resolve(host, 'A'):
					info.append((family, type, proto, None, (addr4, port)))
			elif family == socket.AF_INET6:
				for addr6 in await self.__resolver.resolve(host, 'AAAA'):
					info.append((family, type, proto, None, (addr6, port, 0, 0)))
			elif family in [0, socket.AF_UNSPEC]:
				addrs4, addrs6 = await gather(self.__resolver.resolve(host, 'A'), self.__resolver.resolve(host, 'AAAA'))
				for addr6 in addrs6:
					info.append((socket.AF_INET6, type, proto, None, (addr6, port, 0, 0)))
				for addr4 in addrs4:
					info.append((socket.AF_INET, type, proto, None, (addr4, port)))
		
		return info
	
	def getnameinfo(self, sockaddr, flags=0):
		raise NotImplementedError
	
	async def __open_resolver(self):
		await self.__resolver.open(self)
	
	async def __close_resolver(self):
		await self.__resolver.close()
	
	async def create_connection(self, protocol_factory, host=None, port=None, *,
						  ssl=None, family=0, proto=0, flags=0, sock=None,
						  local_addr=None, server_hostname=None):
		
		gremote_addr = Gio.InetSocketAddress.new_from_string(host, port)
		if local_addr is not None:
			glocal_addr = Gio.InetSocketAddress.new_from_string(*local_addr)
		else:
			glocal_addr = None
		
		if family == socket.AF_INET:
			gfamily = Gio.SocketFamily.IPV4
		elif family == socket.AF_INET6:
			gfamily = Gio.SocketFamily.IPV6
		elif family in [socket.AF_UNSPEC, 0]:
			gfamily = (glocal_addr.get_family() if glocal_addr else None) or (gremote_addr.get_family() if gremote_addr else None)
		else:
			raise ValueError("Unsupported address family.")
		
		if gfamily is None:
			raise ValueError("Address family not specified.")
		if gremote_addr and gremote_addr.get_family() != gfamily:
			raise ValueError("Remote address is not the right family.")
		if glocal_addr and glocal_addr.get_family() != gfamily:
			raise ValueError("Local address is not the right family.")
		
		if proto != 0:
			raise ValueError
		else:
			gproto = Gio.SocketProtocol.TCP
		
		if ssl:
			transport = SSLTransport(gfamily, gproto, sock, flags)
		else:
			transport = TCPTransport(gfamily, gproto, sock, flags)
		protocol = protocol_factory()
		transport.set_protocol(protocol)
		
		if glocal_addr:
			transport.bind(glocal_addr, False)
		await transport.connect(self, gremote_addr)
		if ssl:
			await transport.starttls(self, ssl, server_hostname)
		transport.start()
		
		return transport, protocol

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

	async def create_datagram_endpoint(self, protocol_factory,
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

		if local_addr:
			glocal_addr = Gio.InetSocketAddress.new_from_string(*local_addr)
		else:
			glocal_addr = None
		
		if remote_addr:
			gremote_addr = Gio.InetSocketAddress.new_from_string(*remote_addr)
		else:
			gremote_addr = None
		
		if family == socket.AF_INET:
			gfamily = Gio.SocketFamily.IPV4
		elif family == socket.AF_INET6:
			gfamily = Gio.SocketFamily.IPV6
		elif family in [socket.AF_UNSPEC, 0]:
			gfamily = (glocal_addr.get_family() if glocal_addr else None) or (gremote_addr.get_family() if gremote_addr else None)
		else:
			raise ValueError("Unsupported address family.")
		
		if gfamily is None:
			raise ValueError("Address family not specified.")
		if glocal_addr and glocal_addr.get_family() != gfamily:
			raise ValueError("Local address is not the right family.")
		if gremote_addr and gremote_addr.get_family() != gfamily:
			raise ValueError("Remote address is not the right family.")
		
		if proto != 0:
			raise ValueError
		else:
			gproto = Gio.SocketProtocol.UDP
		
		#if not sock:
		#	sock = socket.socket(family, socket.SOCK_DGRAM, proto)
		#sock.setblocking(False)
		##sock.settimeout(0)
		#if local_addr:
		#	sock.bind(local_addr, reuse_address)
		
		transport = UDPTransport(gfamily, gproto, sock, flags)
		
		protocol = protocol_factory()
		transport.set_protocol(protocol)
		
		if glocal_addr:
			transport.bind(glocal_addr, reuse_address)
		if gremote_addr:
			await transport.connect(self, gremote_addr)
		transport.start()
		
		return transport, protocol
	
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
		self.__signals[sig] = GLib.unix_signal_add(sig, callback, *args)
	
	def remove_signal_handler(self, sig):
		raise NotImplementedError
		GLib.Source.remove(self.__signals[sig])
		self.__signals[sig] = None

	# Task factory.

	def set_task_factory(self, factory):
		self.__task_factory = factory
	
	def get_task_factory(self):
		return self.__task_factory

	# Error handlers.

	def get_exception_handler(self):
		return self.__exception_handler
	
	def set_exception_handler(self, handler):
		self.__exception_handler = handler
	
	def default_exception_handler(self, context):
		print(context) # TODO
	
	def call_exception_handler(self, context):
		if self.__exception_handler is not None:
			self.__exception_handler(self, context)
		else:
			self.default_exception_handler(context)
	
	# Debug flag management.

	def get_debug(self):
		return self.__debug_flag

	def set_debug(self, enabled):
		self.__debug_flag = enabled


class GtkAioEventLoopPolicy(asyncio.events.AbstractEventLoopPolicy):
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
	from asyncio import sleep, set_event_loop_policy, run, gather, create_task, get_running_loop
	from protocol.http.client import Connection1
	
	set_event_loop_policy(GtkAioEventLoopPolicy())
	
	async def testA():
		print("testA", 0)
		await sleep(1)
		print("testA", 1)
		print(await get_running_loop().getaddrinfo('gist.githubusercontent.com', 80))
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
		async with Connection1('http://www.google.com/') as google:
			print((await google.Url().get())[:32])
		
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
