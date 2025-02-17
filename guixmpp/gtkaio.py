#!/usr/bin/python3

"""
Asyncio loop implementation based on GLib. Uses GLib.idle_add() for scheduling tasks.
Seamlessly integrates with asynchronous GLib function. (Each asynchronous GLib function will
behave as it had await inside.)
"""

import gi
if __name__ == '__main__':
	#gi.require_version('Gtk', '3.0')
	gi.require_version('GLib', '2.0')
	gi.require_version('Gio', '2.0')
from gi.repository import GLib, Gio

import asyncio
import asyncio.events
import asyncio.transports

from asyncio import Future, Task, iscoroutine, gather, wrap_future, wait_for, Event, StreamReader, StreamWriter, get_running_loop
from asyncio.tasks import current_task
from asyncio.events import _set_running_loop, Handle, TimerHandle
from asyncio.subprocess import PIPE, STDOUT, DEVNULL
from asyncio.exceptions import InvalidStateError

import socket
import ssl
from math import floor
from collections import deque
import concurrent.futures
from os import strerror, environ, set_blocking, _exit
from signal import SIGTERM, SIGKILL
import sys


if __name__ == '__main__':
	from guixmpp.protocol.dns import AsyncResolver
	from guixmpp.gtkaiopath import Path
else:
	from .protocol.dns import AsyncResolver
	from .gtkaiopath import Path


def _debug_transports(*args):
	#print('_debug_transports', *args)
	pass


def _debug_tasks(*args):
	#print('_debug_tasks', *args)
	pass


def _ret_false(old_fun):
	def new_fun(*args):
		old_fun(*args)
		return False
	new_fun.__name__ = old_fun.__name__
	return new_fun


def idle_add(fun, *args):
	GLib.idle_add(_ret_false(fun), *args)
	
	#def _debug(*args):
	#	print("Running:", fun, *args)
	#	fun(*args)
	#	return False
	#print("Scheduling:", GLib.main_depth(), fun, *args)
	#GLib.idle_add(_debug, *args)


class AllConnectionAttemptsFailedError(ExceptionGroup):
	pass


class BaseTransport(asyncio.transports.BaseTransport):
	def __init__(self, endpoint, channel):
		_debug_transports('BaseTransport.__init__', hex(id(self))[2:])
		self.__endpoint = endpoint
		self.__channel = channel
		self.__watch_in = None
		self.__watch_out = None
		self.__protocol = None
		self.__closing = False
		self.transport_closed = Event()
	
	def __del__(self):
		if hasattr(self, '_BaseTransport__watch_in'):
			self.watch_in(False)
		if hasattr(self, '_BaseTransport__watch_out'):
			self.watch_out(False)
	
	def watching_in(self):
		return self.__watch_in is not None
	
	def watch_in(self, watch_in):
		_debug_transports('BaseTransport.watch_in', hex(id(self))[2:], watch_in)
		if watch_in and (self.__watch_in is None):
			self.__watch_in = GLib.io_add_watch(self.__channel, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self.__event_in)
		elif (not watch_in) and (self.__watch_in is not None):
			GLib.Source.remove(self.__watch_in)
			self.__watch_in = None
	
	def watching_out(self):
		return self.__watch_out is not None
	
	def watch_out(self, watch_out):
		_debug_transports('BaseTransport.watch_out', hex(id(self))[2:], watch_out)
		if watch_out and (self.__watch_out is None):
			self.__watch_out = GLib.io_add_watch(self.__channel, GLib.IO_OUT, self.__event_out)
		elif (not watch_out) and (self.__watch_out is not None):
			GLib.Source.remove(self.__watch_out)
			self.__watch_out = None
	
	def _data_in(self, channel):
		raise NotImplementedError("BaseTransport._data_in")
	
	def _data_out(self, channel):
		raise NotImplementedError("BaseTransport._data_out")
	
	def __event_out(self, channel, condition):
		_debug_transports('BaseTransport.__event_out', hex(id(self))[2:], channel, "in:", bool(condition & GLib.IO_OUT))
		if condition & GLib.IO_OUT:
			result = self._data_out(channel)
			if not result:
				self.__watch_out = None
			return result
	
	def __event_in(self, channel, condition):
		_debug_transports('BaseTransport.__event_in', hex(id(self))[2:], channel, "in:", bool(condition & GLib.IO_IN), "hup:", bool(condition & GLib.IO_HUP), "err:", bool(condition & GLib.IO_ERR))
		
		result = None
		if condition & GLib.IO_IN:
			result = self._data_in(channel) # True - more data to read; None - no more data to read
		
		if condition & GLib.IO_HUP:
			result = False
		
		if condition & GLib.IO_ERR:
			if self.__protocol is not None:
				_debug_transports(' error_received', self.__protocol)
				if hasattr(self.__protocol, 'error_received'):
					idle_add(self.__protocol.error_received, None)
		
		if result is True: # keep receiving events
			return True
		elif result is False: # stop receiving events
			if self.__protocol:
				_debug_transports(' connection_lost', self.__protocol)
				idle_add(self.__protocol.connection_lost, None)
				self.__protocol = None
			self.__watch_in = None
			return False
		elif result is None: # pause receiving events (restore later)
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
		
		_debug_transports('BaseTransport.abort', hex(id(self))[2:])
		
		self.watch_in(False)
		self.watch_out(False)
		
		if self.__channel is not None:
			try:
				self.__channel.shutdown(False)
			except GLib.GError: # ignore exception
				pass
			self.__channel = None
		
		self.close()
	
	def close(self):
		_debug_transports('BaseTransport.close', hex(id(self))[2:])
		
		self.__closing = True
		
		if self.__channel is not None:
			try:
				self.__channel.shutdown(True)
			except (OSError, GLib.GError): # may fail if this is emergency shutown after error
				pass
			self.__channel = None
		
		if self.__endpoint is not None:
			try:
				self.__endpoint.close()
			except (OSError, GLib.GError): # might have been closed by `channel.shutdown()`
				pass
			self.__endpoint = None
		
		self.watch_in(False)
		self.watch_out(False)
		
		if self.__protocol is not None:
			idle_add(self.__protocol.connection_lost, None)
			self.__protocol = None
		
		self.__closing = False
		self.transport_closed.set()
	
	def is_closing(self):
		return self.__closing
	
	def get_extra_info(self, name, default=None):
		try:
			match name:
				case 'peername': # the remote address to which the socket is connected, result of socket.socket.getpeername() (None on error)
					try:
						return self.__endpoint.getpeername() # TODO: check for bugs, possible blocking io
					except AttributeError:
						raise
					except:
						# TODO: warning on error. Documentations says `None` should be returned on error.
						return None
				
				case 'socket': # socket.socket instance
					return self.__endpoint
				
				case 'sockname': # the socket’s own address, result of socket.socket.getsockname()
					return self.__endpoint.getsockname() # TODO: check for bugs, possible blocking io
				
				case 'compression': # the compression algorithm being used as a string, or None if the connection isn’t compressed; result of ssl.SSLSocket.compression()
					return self.__endpoint.compression() # TODO: check for bugs, possible blocking io
				
				case 'cipher': # a three-value tuple containing the name of the cipher being used, the version of the SSL protocol that defines its use, and the number of secret bits being used; result of ssl.SSLSocket.cipher()
					return default
				
				case 'peercert': # peer certificate; result of ssl.SSLSocket.getpeercert()
					return self.__endpoint.getpeercert() # TODO: check for bugs, possible blocking io
				
				case 'sslcontext': # ssl.SSLContext instance
					return default
				
				case 'ssl_object': # ssl.SSLObject or ssl.SSLSocket instance
					return self.__endpoint
				
				case 'pipe': # pipe object
					return self.__endpoint
				
				case 'subprocess': # subprocess.Popen instance
					return self.__endpoint
				
				#case 'iochannel':
				#	return self.__channel
				
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
	
	async def start(self):
		_debug_transports('BaseTransport.start', hex(id(self))[2:])
		
		protocol = self.get_protocol()
		if protocol is not None:
			protocol.connection_made(self)
		
		self.watch_in(True)


class NetworkTransport(BaseTransport):
	def __init__(self, gfamily, gstype, gproto, sock, flags):
		_debug_transports('NetworkTransport.__init__', hex(id(self))[2:])
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
	
	def _read_raw(self):
		sock = self.get_extra_info('read_endpoint')
		return sock.recv(4096)
	
	def _write_raw(self, data):
		sock = self.get_extra_info('write_endpoint')
		return sock.send(data)
	
	def _data_out(self, channel):
		_debug_transports('NetworkTransport._data_out', hex(id(self))[2:], channel)
		
		if hasattr(self, '_NetworkTransport__established'):
			sock = self.get_extra_info('socket')
			try:
				self.__errno = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
			except OSError as error:
				self.__errno = error.errno
			self.__established.set()
			#if not errno:
			#	self.__established.set_result(None)
			#else:
			#	self.__established.set_exception(OSError("Error establishing connection", errno))
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
			self.__established = Event()
			self.watch_out(True)
			await self.__established.wait()
			if self.__errno:
				raise OSError(strerror(self.__errno))
			del self.__established, self.__errno


class UDPTransport(NetworkTransport, asyncio.transports.DatagramTransport):
	def __init__(self, gfamily, gproto, sock, flags):
		_debug_transports('UDPTransport.__init__', hex(id(self))[2:])
		super().__init__(gfamily, Gio.SocketType.DATAGRAM, gproto, sock, flags)
	
	def _data_in(self, channel):
		_debug_transports('UDPTransport._data_in', hex(id(self))[2:], channel)
		
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
				if protocol is not None and hasattr(protocol, 'error_received'):
					idle_add(protocol.error_received, error)
			else:
				if protocol is not None:
					idle_add(protocol.datagram_received, data, addr)
		
		return True
	
	def sendto(self, data, addr=None):
		_debug_transports('UDPTransport.sendto', hex(id(self))[2:], len(data), addr)
		
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
			if protocol is not None and hasattr(protocol, 'error_received'):
				idle_add(protocol.error_received, error)


class ReadTransport(BaseTransport, asyncio.transports.ReadTransport):
	def __init__(self):
		_debug_transports('ReadTransport.__init__', hex(id(self))[2:])
	
	def _data_in(self, channel):
		_debug_transports('ReadTransport._data_in', hex(id(self))[2:], channel)
		
		sock = self.get_extra_info('read_endpoint')
		if not sock:
			return False
		
		protocol = self.get_protocol()
		if protocol is None:
			return False
		
		while True:
			try:
				data = self._read_raw()
			except (BlockingIOError, ssl.SSLWantReadError):
				return True
			else:
				if data:
					_debug_transports(' data_received', len(data), repr(data) if len(data) < 10 else "")
					idle_add(protocol.data_received, data)
				else:
					_debug_transports(' eof_received')
					if hasattr(protocol, 'eof_received'):
						idle_add(protocol.eof_received)
					return False
		
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
		_debug_transports('WriteTransport.__init__', hex(id(self))[2:])
		self.__write_high = 4096
		self.__write_low = 4096
		self.__write_buffer = deque()
		self.__writing = True
		self.write_buffer_empty = Event()
		self.write_buffer_empty.set() # empty by default
		self.__closing = False
	
	def _data_out(self, channel):
		_debug_transports('WriteTransport._data_out', hex(id(self))[2:], channel)
		
		sock = self.get_extra_info('write_endpoint')
		if not sock:
			return False
		
		protocol = self.get_protocol()
		if protocol is None:
			return False
		
		while self.__write_buffer:
			data = self.__write_buffer.popleft()
			l = self._write_raw(data)
			if l < len(data):
				self.__write_buffer.insert(0, data[l:])
				break
		
		if not self.__writing:
			if self.get_write_buffer_size() <= self.__write_low:
				self.__writing = True
				protocol.resume_writing()
		
		if not self.__write_buffer:
			_debug_transports('WriteTransport._data_out (write_buffer_empty=True)', hex(id(self))[2:], channel)
			if self.__closing:
				super().close()
			self.write_buffer_empty.set()
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
		
		_debug_transports('WriteTransport.write', hex(id(self))[2:], len(data))
		
		if self.__closing:
			raise RuntimeError("Transport closed.")
		
		if data:
			_debug_transports('WriteTransport.write (write_buffer_empty=False)', hex(id(self))[2:], len(data))
			self.write_buffer_empty.clear()
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
		self.close()
	
	def can_write_eof(self):
		"""Return True if this transport supports write_eof(), False if not."""
		return True
	
	def abort(self):
		self.write_buffer_empty.clear()
		self.__write_buffer.clear()
		self.__closing = False
		super().abort()
		self.write_buffer_empty.set()
	
	def close(self):
		if self.__closing: return
		self.__closing = True
		if not self.__write_buffer:
			super().close()


class TCPTransport(NetworkTransport, ReadTransport, WriteTransport, asyncio.transports.Transport):
	def __init__(self, gfamily, gproto, sock, flags):
		_debug_transports('TCPTransport.__init__', hex(id(self))[2:])
		NetworkTransport.__init__(self, gfamily, Gio.SocketType.STREAM, gproto, sock, flags)
		ReadTransport.__init__(self)
		WriteTransport.__init__(self)
	
	def _data_out(self, channel):
		_debug_transports('TCPTransport._data_out', hex(id(self))[2:], channel)
		
		result = NetworkTransport._data_out(self, channel)
		if result in (True, False):
			return result
		
		return WriteTransport._data_out(self, channel)


class SSLTransport(TCPTransport):
	def __init__(self, *args):
		_debug_transports('SSLTransport.__init__', hex(id(self))[2:])
		super().__init__(*args)
	
	async def starttls(self, loop, ssl_context, server_side=False, server_hostname=None): # TODO: timeouts
		sock = self.get_extra_info('socket')
		if not sock:
			return False
		
		sslsock = self.__ssl_socket = ssl_context.wrap_socket(sock, do_handshake_on_connect=False, server_side=server_side, server_hostname=server_hostname)
		
		while True:
			try:
				sslsock.do_handshake()
				break
			except ssl.SSLWantReadError:
				self.__hands_shaken_in = Event()
				self.watch_in(True)
				await self.__hands_shaken_in.wait()
				del self.__hands_shaken_in
			except ssl.SSLWantWriteError:
				self.__hands_shaken_out = Event()
				self.watch_out(True)
				await self.__hands_shaken_out.wait()
				del self.__hands_shaken_out
	
	def get_extra_info(self, name, default=None):
		match name:
			case 'ssl_object':
				return self.__ssl_socket
				
			case 'read_endpoint':
				return self.__ssl_socket
			
			case 'write_endpoint':
				return self.__ssl_socket
			
			case 'cipher':
				return self.__ssl_socket.cipher()
			
			case _:
				return super().get_extra_info(name, default)
	
	def _data_out(self, channel):
		_debug_transports('SSLTransport._data_out', hex(id(self))[2:], channel)
		
		if hasattr(self, '_SSLTransport__hands_shaken_out'):
			self.__hands_shaken_out.set() #.set_result(None)
			return None
		else:
			try:
				return super()._data_out(channel)
			except ssl.SSLEOFError as error:
				if (protocol := self.get_protocol()) is not None:
					_debug_transports(' SSL EOF', protocol)
					if hasattr(protocol, 'eof_received'):
						idle_add(protocol.eof_received)
				return None
	
	def _data_in(self, channel):
		_debug_transports('SSLTransport._data_in', hex(id(self))[2:], channel)
		
		if hasattr(self, '_SSLTransport__hands_shaken_in'):
			self.__hands_shaken_in.set() #.set_result(None)
			return None
		else:
			try:
				return super()._data_in(channel)
			except ssl.SSLError as error:
				if (protocol := self.get_protocol()) is not None:
					_debug_transports(' SSL exception', protocol)
					if hasattr(protocol, 'error_received'):
						idle_add(protocol.error_received, error)
				return None


class GioStreamTransport:
	def __init__(self, stream):
		_debug_transports('GioStreamTransport.__init__', hex(id(self))[2:])
		#print(type(stream), stream.get_fd.__doc__)
		fd = stream.get_fd()
		set_blocking(fd, False)
		channel = GLib.IOChannel.unix_new(fd)
		channel.set_encoding(None)
		BaseTransport.__init__(self, stream, channel)
	
	def _read_raw(self):
		stream = self.get_extra_info('read_endpoint')
		assert stream.can_poll()
		if not stream.is_readable():
			raise BlockingIOError
		return stream.read_bytes(4096, None).get_data()
	
	def _write_raw(self, data):
		stream = self.get_extra_info('write_endpoint')
		assert stream.can_poll()
		if not stream.is_writable():
			raise BlockingIOError
		return stream.write(data)


class InputStreamTransport(GioStreamTransport, ReadTransport):
	def __init__(self, stream):
		_debug_transports('InputStreamTransport.__init__', hex(id(self))[2:], stream)
		
		GioStreamTransport.__init__(self, stream)
		ReadTransport.__init__(self)


class OutputStreamTransport(GioStreamTransport, WriteTransport):
	def __init__(self, stream):
		_debug_transports('InputStreamTransport.__init__', hex(id(self))[2:], stream)
		
		GioStreamTransport.__init__(self, stream)
		WriteTransport.__init__(self)
	
	async def start(self):
		_debug_transports('InputStreamTransport.start', hex(id(self))[2:])
		
		protocol = self.get_protocol()
		if protocol is not None:
			protocol.connection_made(self)


class SubprocessTransport(BaseTransport, asyncio.transports.SubprocessTransport):
	class ReaderProtocol:
		def __init__(self, pipe_fd, subprocess_transport):
			self.pipe_fd = pipe_fd
			self.subprocess_transport = subprocess_transport
			self._stream_reader = None
		
		def connection_made(self, pipe_transport):
			_debug_transports('SubprocessTransport.ReaderProtocol.connection_made', hex(id(self))[2:], pipe_transport)
		
		def connection_lost(self, reason):
			_debug_transports('SubprocessTransport.ReaderProtocol.connection_lost', hex(id(self))[2:], reason)
			protocol = self.subprocess_transport.get_protocol()
			if protocol is None:
				return
			
			assert protocol._transport is not None, repr(protocol) + "@" + hex(id(protocol))[2:]
			
			if self._stream_reader is not None:
				_debug_transports(' forwarding connection lost', self.pipe_fd)
				self._stream_reader.feed_eof()
			else:
				_debug_transports(' pipe_connection_lost', hex(id(self))[2:], self.pipe_fd, reason, protocol)
				protocol.pipe_connection_lost(self.pipe_fd, reason)
		
		def data_received(self, data):
			_debug_transports('SubprocessTransport.ReaderProtocol.data_received', hex(id(self))[2:], len(data))
			protocol = self.subprocess_transport.get_protocol()
			if protocol is None:
				return
			
			if self._stream_reader is not None:
				_debug_transports(' forwarding data', self.pipe_fd, len(data))
				self._stream_reader.feed_data(data)
			else:
				_debug_transports(' pipe_data_received', hex(id(self))[2:], self.pipe_fd, len(data), protocol)
				protocol.pipe_data_received(self.pipe_fd, data)
	
	class WriterProtocol:
		def __init__(self, pipe_fd, subprocess_transport):
			self.pipe_fd = pipe_fd
			self.subprocess_transport = subprocess_transport
			self._stream_writer = None
		
		async def _drain_helper(self):
			pass # TODO: poll the fd to check if writing blocks
		
		def connection_made(self, pipe_transport):
			_debug_transports('SubprocessTransport.WriterProtocol.connection_made', hex(id(self))[2:], pipe_transport)
		
		def connection_lost(self, reason):
			_debug_transports('SubprocessTransport.WriterProtocol.connection_lost', hex(id(self))[2:], reason)
			protocol = self.subprocess_transport.get_protocol()
			if protocol is None:
				return
			
			assert protocol._transport is not None, repr(protocol) + "@" + hex(id(protocol))[2:]
			
			if self._stream_writer is not None:
				pass
				#_debug_transports(' forwarding connection lost', self.pipe_fd)
				#self._stream_writer.feed_eof()
			else:
				_debug_transports(' pipe_connection_lost', hex(id(self))[2:], self.pipe_fd, reason, protocol)
				protocol.pipe_connection_lost(self.pipe_fd, reason)
	
	def __init__(self, cmd, stdin, stdout, stderr, pass_fds=(), loop=None, **kwargs):
		_debug_transports('SubprocessTransport.__init__', hex(id(self))[2:], cmd)
		
		self.__loop = loop
		
		self.__returncode = None
		self.__finished = Event()
		self.__pipe = {}
		
		flags = Gio.SubprocessFlags.NONE
		
		if stdin == DEVNULL or stdin == None:
			pass
		elif stdin == PIPE:
			flags |= Gio.SubprocessFlags.STDIN_PIPE
		elif isinstance(stdin, int):
			pass
		elif hasattr(stdin, 'fileno'):
			stdin = stdin.fileno()
		else:
			raise ValueError("Invalid value for stdin pipe.")
		
		if stdout == None:
			pass
		elif stdout == PIPE:
			flags |= Gio.SubprocessFlags.STDOUT_PIPE
		elif stdout == DEVNULL:
			flags |= Gio.SubprocessFlags.STDOUT_SILENCE
		elif isinstance(stdout, int):
			pass
		elif hasattr(stdout, 'fileno'):
			stdout = stdout.fileno()
		else:
			raise ValueError("Invalid value for stdout pipe.")
		
		if stderr == None:
			pass
		elif stderr == PIPE:
			flags |= Gio.SubprocessFlags.STDERR_PIPE
		elif stderr == DEVNULL:
			flags |= Gio.SubprocessFlags.STDERR_SILENCE
		elif stderr == STDOUT:
			flags |= Gio.SubprocessFlags.STDERR_MERGE
		elif isinstance(stderr, int):
			pass
		elif hasattr(stderr, 'fileno'):
			stderr = stderr.fileno()
		else:
			raise ValueError("Invalid value for stderr pipe.")
		
		launcher = self.__launcher = Gio.SubprocessLauncher.new(flags)
		
		if isinstance(stdin, int):
			launcher.take_stdin_fd(stdin)
		if isinstance(stdout, int):
			launcher.take_stdout_fd(stdout)
		if isinstance(stderr, int):
			launcher.take_stderr_fd(stderr)
		
		for fd in pass_fds:
			launcher.take_fd(fd, fd)
		
		self.__cmd = cmd
		
		super().__init__(None, None)
	
	def __child_exit(self, pid, status):
		_debug_transports('SubprocessTransport.__child_exit', hex(id(self))[2:], pid, status)
		self.__returncode = status
		self.__finished.set()
		
		protocol = self.get_protocol()
		if not protocol:
			return
		
		_debug_transports(' process_exited', protocol)
		protocol.process_exited()
	
	def __writer_drain_helper(self, protocol, orig_drain_helper):
		"Original drain() waits only for flow control commands. Wait also for stdin write buffer to empty."
		async def _drain_helper():
			_debug_transports(' _drain_helper', protocol)
			_debug_transports(' _drain_helper.1', protocol)
			await orig_drain_helper()
			_debug_transports(' _drain_helper.2', protocol)
			if stdin := self.get_pipe_transport(0):
				_debug_transports(' _drain_helper.3', protocol)
				await stdin.write_buffer_empty.wait()
				_debug_transports(' _drain_helper.4', protocol)
			_debug_transports(' _drain_helper.5', protocol)
		return _drain_helper()
	
	def register_pipe_transport(self, fd, transport):
		self.__pipe[fd] = transport
	
	async def start(self):
		_debug_transports('SubprocessTransport.start', hex(id(self))[2:])
		
		loop = self.__loop
		if loop is None:
			loop = get_running_loop()
		
		self._BaseTransport__endpoint = self.__child = child = self.__launcher.spawnv(self.__cmd)
		del self.__launcher
		self.__pid = int(child.get_identifier())
		GLib.child_watch_add(self.__pid, self.__child_exit)
		
		if stdin_pipe := child.get_stdin_pipe():
			transport, _ = await loop.connect_write_pipe(lambda: self.WriterProtocol(0, self), stdin_pipe)
			self.register_pipe_transport(0, transport)
		if stdout_pipe := child.get_stdout_pipe():
			transport, _ = await loop.connect_read_pipe(lambda: self.ReaderProtocol(1, self), stdout_pipe)
			self.register_pipe_transport(1, transport)
		if stderr_pipe := child.get_stderr_pipe():
			transport, _ = await loop.connect_read_pipe(lambda: self.ReaderProtocol(2, self), stderr_pipe)
			self.register_pipe_transport(2, transport)
		
		protocol = self.get_protocol()
		if not protocol:
			return
		
		orig_drain_helper = protocol._drain_helper
		protocol._drain_helper = lambda: self.__writer_drain_helper(protocol, orig_drain_helper)
		
		_debug_transports(' connection_made', hex(id(self))[2:], protocol)
		protocol.connection_made(self)
	
	def get_pid(self):
		"Return the subprocess process id as an integer."
		return self.__pid
	
	def get_pipe_transport(self, fd):
		"""Return the transport for the communication pipe corresponding to the integer file descriptor fd:
		0: readable streaming transport of the standard input (stdin), or None if the subprocess was not created with stdin=PIPE
		1: writable streaming transport of the standard output (stdout), or None if the subprocess was not created with stdout=PIPE
		2: writable streaming transport of the standard error (stderr), or None if the subprocess was not created with stderr=PIPE
		other fd: None"""
		
		try:
			return self.__pipe[fd]
		except KeyError:
			return None
	
	def get_returncode(self):
		"Return the subprocess return code as an integer or None if it hasn’t returned, which is similar to the subprocess.Popen.returncode attribute."
		return self.__returncode
	
	def send_signal(self, signal):
		"Send the signal number to the subprocess, as in subprocess.Popen.send_signal()."
		self.__child.send_signal(signal)
	
	def kill(self):
		"""Kill the subprocess.
		On POSIX systems, the function sends SIGKILL to the subprocess. On Windows, this method is an alias for terminate().
		See also subprocess.Popen.kill()."""
		self.send_signal(SIGKILL)
	
	def terminate(self):
		"""Stop the subprocess.
		On POSIX systems, this method sends SIGTERM to the subprocess. On Windows, the Windows API function TerminateProcess() is called to stop the subprocess.
		See also subprocess.Popen.terminate()."""
		self.send_signal(SIGTERM)
	
	def close(self):
		"Kill the subprocess by calling the kill() method."
		if self.__returncode is not None:
			return
		self.__child.force_exit()
	
	async def _wait(self):
		await self.__finished.wait()
		return self.__returncode


async def _program_exists(path):
	try:
		return 'x' in await Path(path).getmode()
	except FileNotFoundError:
		return False


class GtkAioEventLoop(asyncio.events.AbstractEventLoop):
	def __init__(self, app=None, argv=()):
		self.__closed = False
		self.__task_factory = None
		self.__debug_flag = False
		self.__exception_handler = None
		self.__completing = None
		self.__completing_done = False
		self.__signals = {}
		self.__resolver = AsyncResolver() # DNS resolver from `guixmpp/protocol/dns/client.py`
		self.__executor = concurrent.futures.ThreadPoolExecutor() # TODO
		self.__app = app
		self.__main_level = 0
		self.__main_quit = False
		self.__argv = argv
		self.__use_app = False
		self.__loop_initialized = False
		self.__handle_queue = deque()
	
	def __is_special_method(self, future):
		try:
			qualname = future.__qualname__.split('.')
			if len(qualname) == 2 and qualname[1].startswith('__'):
				qualname[1] = '_' + qualname[0] + qualname[1]
			qualname = '.'.join(qualname)
			special_method = eval(qualname).special_method
			_debug_tasks('__is_special_method', future, qualname, special_method)
		except AttributeError:
			special_method = False
		
		return special_method
	
	def __run_future(self, future):
		assert self.__completing is None # FIXME: will fail if one task raised exception and another task started before the loop shutdown
		
		if self.is_running() or self.is_closed():
			raise RuntimeError(f"Invalid loop state: running={self.is_running()} closed={self.is_closed()}.")
		
		_set_running_loop(self)
		
		special_method = self.__is_special_method(future)
		
		_debug_tasks('__run_future', future, special_method)
		
		self.__use_app = (self.__app is not None) and (not special_method)
		if iscoroutine(future):
			_debug_tasks('create_task', future)
			future = self.create_task(future, name=future.__name__)
		self.__completing = future
		self.__completing_done = False
		
		GLib.idle_add(self._check_completing_state)
		
		if not self.__use_app:
			_debug_tasks("Main begin", future)
			#try:
			#	main = Gtk.main
			#except AttributeError:
			self.__main_level += 1
			context = GLib.MainContext.default()
			self.__main_quit = False
			while not self.__main_quit:
				#print("iteration.begin", context.pending())
				context.iteration()
				#print("iteration.end")
			self.__main_level -= 1
			#else:
			#	main()
			_debug_tasks("Main end", future)
		else:
			#_debug_tasks("__app.hold")
			#self.__app.hold()
			_debug_tasks("__app.run begin")
			self.__app.app_result = self.__app.run(self.__argv)
			_debug_tasks("__app.run end", self.__app.app_result)
			self.__app = None
		
		exception = None
		result = None
		if self.__completing is not None:
			try:
				result = self.__completing.result()
			except InvalidStateError:
				result = None
			except BaseException as error:
				exception = error
		
		self.__completing = None
		self.__use_app = False
		
		_set_running_loop(None)
		
		if exception is not None:
			raise exception
		else:
			return result
	
	def run_forever(self):
		"""Run the event loop until stop() is called."""
		
		return self.run_until_complete(None)
	
	def run_until_complete(self, future):
		"""Run the event loop until a Future is done.
		Return the Future's result, or raise its exception.
		"""
		
		special_method = self.__is_special_method(future)
		
		_debug_tasks("run_until_complete", future, special_method)
		
		self.__loop_initialized = True
		if not special_method:
			_debug_tasks("spawn __begin_loop")
			self.__run_future(self.__begin_loop())
		
		while self.__handle_queue:
			_debug_tasks("executing queued handle")
			handle = self.__handle_queue.pop()
			idle_add(self.__run_handle, handle)
		
		exception = None
		try:
			result = self.__run_future(future)
		except BaseException as error:
			exception = error
		
		if not special_method:
			_debug_tasks("spawn __end_loop")
			self.__run_future(self.__end_loop())
		self.__loop_initialized = False
		
		if exception is not None:
			raise exception
		else:
			return result
	
	async def __begin_loop(self):
		_debug_tasks("__begin_loop")
		await self.__resolver.open(self)
	
	__begin_loop.special_method = True
	
	async def __end_loop(self):
		_debug_tasks("__end_loop")
		await self.__resolver.close()
	
	__end_loop.special_method = True
	
	def _check_completing_state(self):
		if self.__completing is None:
			return False
		
		if not self.__completing.done():
			return False
		
		if self.__completing_done:
			return False
		else:
			self.__completing_done = True
		
		if not self.__use_app:
			#try:
			#	Gtk.main_quit()
			#except AttributeError:
			if self.__main_level > 0:
				self.__main_quit = True
		#elif self.__app is not None:
		#	_debug_tasks("__app.release", self.__completing)
		#	self.__app.release()
		
		return False
	
	def stop(self):
		"""Stop the event loop as soon as reasonable.
		Exactly how soon that is may depend on the implementation, but
		no more I/O callbacks should be scheduled.
		"""
		
		if not self.is_running() or self.is_closed():
			raise RuntimeError
		
		if self.__app is None:
			#try:
			#	Gtk.main_quit()
			#except AttributeError:
			if self.__main_level > 0 and GLib.MainContext.default().pending():
				self.__main_quit = True
		else:
			self.__app.quit()
	
	def is_running(self):
		"""Return whether the event loop is currently running."""
		#try:
		#	return Gtk.main_level() > 0
		#except AttributeError:
		return self.__main_level > 0
	
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
			raise RuntimeError("Running loop can not be closed.")
		self.__closed = True
	
	async def shutdown_asyncgens(self):
		"""Shutdown all active asynchronous generators."""
		#print("shutdown_asyncgens")
		pass # FIXME
	
	shutdown_asyncgens.special_method = True
	
	async def shutdown_default_executor(self, timeout=None):
		if self.__executor:
			self.__executor.shutdown()
	
	shutdown_default_executor.special_method = True
	
	# Methods scheduling callbacks.  All these return Handles.
	
	def _timer_handle_cancelled(self, handle):
		"""Notification that a TimerHandle has been cancelled."""
		pass
	
	def __run_handle(self, handle):
		#_debug_tasks('__run_handle', handle)
		try:
			if not handle._cancelled:
				#_debug_tasks('__run_handle._run', handle)
				handle._run()
		except BaseException as exc:
			self.call_exception_handler({'exception':exc})
		finally:
			self._check_completing_state()
			return False
	
	def call_soon(self, callback, *args, context=None):
		handle = Handle(callback, args, self, context=context)
		if self.__loop_initialized:
			idle_add(self.__run_handle, handle)
		else:
			_debug_tasks("handle queued")
			self.__handle_queue.append(handle)
		return handle
	
	call_soon_threadsafe = call_soon
	
	#def call_soon_threadsafe(self, callback, *args, context=None):
	#	handle = Handle(callback, args, self, context=context)
	#	GLib.idle_add(self.__run_handle, handle)
	#	return handle
	
	def call_later(self, delay, callback, *args, context=None):
		_debug_tasks('call_later', delay, callback)
		current_time = self.time()
		when = current_time + delay
		handle = TimerHandle(when, callback, args, self, context=context)
		GLib.timeout_add(delay * 1000, self.__run_handle, handle)
		return handle
	
	def call_at(self, when, callback, *args, context=None):
		_debug_tasks('call_at', when, callback)
		current_time = self.time()
		delay = when - current_time
		handle = TimerHandle(when, callback, args, self, context=context)
		GLib.timeout_add(delay * 1000, self.__run_handle, handle)
		return handle
	
	def time(self):
		return GLib.get_monotonic_time() / 10**6
	
	def create_future(self):
		return Future(loop=self)
	
	# Method scheduling a coroutine object: create a task.
	
	def create_task(self, coro, *, name=None, context=None):
		if self.__task_factory is None:
			if name is None:
				try:
					name = 'Coroutine: ' + coro.__name__
				except AttributeError:
					pass
			return Task(coro, loop=self, name=name, context=context)
		else:
			task = self.__task_factory(self, coro, context)
			if name:
				task.set_name(name)
			return task
	
	# Methods for interacting with threads.
	
	def run_in_executor(self, executor, func, *args):
		if executor is None:
			executor = self.__executor
		future = executor.submit(func, *args)
		return wrap_future(future, loop=self)
	
	def set_default_executor(self, executor):
		self.__executor = executor
	
	# Network I/O methods returning Futures.
	
	async def getaddrinfo(self, host, port, *, family=0, type=0, proto=0, flags=0):
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
		raise NotImplementedError("getnameinfo")
	
	async def __try_addrs(self, host, port, family, proto):
		try:
			gremote_addr = Gio.InetSocketAddress.new_from_string(host, port)
		except TypeError:
			pass
		else:
			yield gremote_addr, family, proto
			return
		
		addrs = await self.getaddrinfo(host, port)
		if not addrs:
			raise ConnectionError(f"Could not resolve hostname: {host}")
		
		for nfamily, ntype_, nproto, cname, addr_port in addrs:
			if family and family != nfamily: continue
			#if proto and proto != nproto: continue
			nhost = addr_port[0]
			nport = addr_port[1]
			gremote_addr = Gio.InetSocketAddress.new_from_string(nhost, nport)
			yield gremote_addr, nfamily, proto
	
	async def create_connection(self, protocol_factory, host=None, port=None, *, ssl=None, family=0, proto=0, flags=0, sock=None, local_addr=None, server_hostname=None):
		if local_addr is not None:
			glocal_addr = Gio.InetSocketAddress.new_from_string(*local_addr)
		else:
			glocal_addr = None
		
		errors = []
		
		async for gremote_addr, family, proto in self.__try_addrs(host, port, family, proto):
			try:
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
					raise ValueError # TODO
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
					await transport.starttls(self, ssl, False, server_hostname)
				await transport.start()
			except Exception as error:
				errors.append(error)
			else:
				return transport, protocol
		
		raise AllConnectionAttemptsFailedError(f"Could not establish connection to {host}:{port}: {' '.join(str(_error) for _error in errors)}", errors)
	
	def create_server(self, protocol_factory, host=None, port=None, *, family=socket.AF_UNSPEC, flags=socket.AI_PASSIVE, sock=None, backlog=100, ssl=None, reuse_address=None, reuse_port=None):
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
		raise NotImplementedError("create_server")
	
	async def start_tls(self, transport, protocol, sslcontext, *, server_side=False, server_hostname=None, ssl_handshake_timeout=None, ssl_shutdown_timeout=None):
		"Upgrade existing TCP transport to TLS."
		transport.watch_in(False)
		transport.watch_out(False)
		ssl_transport = SSLTransport(0, 0, transport.get_extra_info('socket'), 0)
		ssl_transport.set_protocol(protocol)
		await ssl_transport.starttls(self, sslcontext, server_side=server_side, server_hostname=server_hostname)
		ssl_transport.watch_in(True)
		return ssl_transport
	
	def create_unix_connection(self, protocol_factory, path, *, ssl=None, sock=None, server_hostname=None):
		raise NotImplementedError("create_unix_connection")
	
	def create_unix_server(self, protocol_factory, path, *, sock=None, backlog=100, ssl=None):
		"""A coroutine which creates a UNIX Domain Socket server.
		The return value is a Server object, which can be used to stop the service.
		path is a str, representing a file systsem path to bind the server socket to.
		sock can optionally be specified in order to use a preexisting socket object.
		backlog is the maximum number of queued connections passed to listen() (defaults to 100).
		ssl can be set to an SSLContext to enable SSL over the accepted connections.
		"""
		raise NotImplementedError("create_unix_server")
	
	async def create_datagram_endpoint(self, protocol_factory, local_addr=None, remote_addr=None, *, family=0, proto=0, flags=0, reuse_address=None, reuse_port=None, allow_broadcast=None, sock=None):
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
		await transport.start()
		
		return transport, protocol
	
	# Pipes and subprocesses.
	
	async def connect_read_pipe(self, protocol_factory, pipe):
		"""Register read pipe in event loop. Set the pipe to non-blocking mode.
		
		protocol_factory should instantiate object with Protocol interface.
		pipe is a file-like object.
		Return pair (transport, protocol), where transport supports the
		ReadTransport interface."""
		# The reason to accept file-like object instead of just file descriptor
		# is: we need to own pipe and close it at transport finishing
		# Can got complicated errors if pass f.fileno(),
		# close fd in pipe transport then close f and vise versa.
		
		if isinstance(pipe, int):
			pipe = Gio.UnixInputStream.new(pipe, True)
		elif hasattr(pipe, 'fileno'):
			pipe = Gio.UnixInputStream.new(pipe.fileno(), True)
		
		transport = InputStreamTransport(pipe)
		
		protocol = protocol_factory()
		transport.set_protocol(protocol)
		
		await transport.start()
		
		return transport, protocol
	
	async def connect_write_pipe(self, protocol_factory, pipe):
		"""Register write pipe in event loop.

		protocol_factory should instantiate object with BaseProtocol interface.
		Pipe is file-like object already switched to nonblocking.
		Return pair (transport, protocol), where transport support
		WriteTransport interface."""
		# The reason to accept file-like object instead of just file descriptor
		# is: we need to own pipe and close it at transport finishing
		# Can got complicated errors if pass f.fileno(),
		# close fd in pipe transport then close f and vise versa.
		
		if isinstance(pipe, int):
			pipe = Gio.UnixOutputStream.new(pipe, True)
		elif hasattr(pipe, 'fileno'):
			pipe = Gio.UnixOutputStream.new(pipe.fileno(), True)
		
		transport = OutputStreamTransport(pipe)
		
		protocol = protocol_factory()
		transport.set_protocol(protocol)
		
		await transport.start()
		
		return transport, protocol
	
	async def subprocess_shell(self, protocol_factory, cmd, *, stdin=None, stdout=None, stderr=None, use_shell=None, capture_output=False, **kwargs):
		if capture_output:
			stdout = stderr = PIPE
		
		transport = SubprocessTransport([use_shell or environ.get('SHELL', '/bin/sh'), '-c', cmd], stdin=stdin, stdout=stdout, stderr=stderr, **kwargs)
		
		protocol = protocol_factory()
		transport.set_protocol(protocol)
		
		await transport.start()
		
		return transport, protocol
	
	async def subprocess_exec(self, protocol_factory, *args, stdin=None, stdout=None, stderr=None, use_path=None, executable=None, capture_output=False, **kwargs):
		if executable is None and not args[0].startswith('/') and not args[0].startswith('.'):
			for path_part in (use_path if use_path is not None else environ.get('PATH', '.:/usr/bin:/bin').split(':')):
				if await _program_exists(str(path_part) + '/' + args[0]):
					executable = str(path_part) + '/' + args[0]
					break
			else:
				raise IOError(f"Program not found in path: {args[0]}")
		
		if capture_output:
			stdout = stderr = PIPE
		
		transport = SubprocessTransport(args, stdin=stdin, stdout=stdout, stderr=stderr, executable=executable, **kwargs)
		
		protocol = protocol_factory()
		transport.set_protocol(protocol)
		
		await transport.start()
		
		return transport, protocol
	
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
		self.__signals[sig] = GLib.unix_signal_add(GLib.PRIORITY_HIGH, sig, callback, args)
	
	def remove_signal_handler(self, sig):
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
		if 'message' in context and 'exception' not in context:
			print(context['message'])
		
		if 'exception' in context:
			if self.__completing is not None:
				self.__completing.cancel()
			self.__completing = self.create_future()
			self.__completing.set_exception(context['exception'])
			if self.__app is not None:
				self.__app.quit()
			else:
				#try:
				#	Gtk.main_quit()
				#except AttributeError:
				if self.__main_level > 0 and GLib.MainContext.default().pending():
					self.__main_quit = True
	
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
			raise RuntimeError("Loop is None. Call set_event_loop first.")
		return self.loop

	def set_event_loop(self, loop):
		"""Set the event loop for the current context to loop."""
		self.loop = loop

	def new_event_loop(self):
		"""Create and return a new event loop object according to this
		policy's rules. If there's need to set this loop as the event loop for
		the current context, set_event_loop must be called explicitly."""
		return GtkAioEventLoop()
	
	## Child processes handling (Unix only).
	#
	#def get_child_watcher(self):
	#	"Get the watcher for child processes."
	#	raise NotImplementedError("get_child_watcher")
	#
	#def set_child_watcher(self, watcher):
	#	"""Set the watcher for child processes."""
	#	raise NotImplementedError("set_child_watcher")


class GtkAioAppEventLoopPolicy(GtkAioEventLoopPolicy):
	def __init__(self, app, argv):
		super().__init__()
		self.__app = app
		self.__argv = argv
	
	def new_event_loop(self):
		return GtkAioEventLoop(self.__app, self.__argv)


if __debug__ and __name__ == '__main__':
	from sys import argv
	
	if len(argv) == 4 and argv[1] == '--test-pipes':
		from os import fdopen, close, set_blocking
		#from time import sleep
		
		r_fd = int(argv[2])
		w_fd = int(argv[3])
		
		set_blocking(r_fd, True)
		set_blocking(w_fd, True)
		
		read_pipe = fdopen(r_fd, 'rb', buffering=0)
		write_pipe = fdopen(w_fd, 'wb', buffering=0)
		
		while ch := read_pipe.read(5):
			assert ch in frozenset({b"12345", b"6789.", b".....", b"...!", b"abcde", b"fgh.."}), repr(ch)
		
		print("writing...")
		write_pipe.write(b"aaa\n")
		write_pipe.flush()
		
		quit()
	
	from asyncio import sleep, set_event_loop_policy, run, gather, create_task, create_subprocess_exec
	from protocol.http.client import Connection1
	
	set_event_loop_policy(GtkAioEventLoopPolicy())
	
	#async def test_basic():
	#	print("test_basic")
	
	#run(test_basic())
	
	async def test_process():
		print("test_process")
		child = await create_subprocess_exec('./examples/sample_child.py', stdin=PIPE, stdout=PIPE)
		
		#print(dir(child))
		child.stdin.writelines([b"!abcdefghkk\n", b"!12345678\n"])
		child.stdin.write(b"wjhwejkh\n")
		print("drain")
		await child.stdin.drain()
		child.stdin.write(b"eljelsd\n")
		print("drain")
		await child.stdin.drain()
		
		child.stdin.close()
		#print("wait_closed")
		#await child.stdin.wait_closed()
		
		async for ln in child.stdout:
			print(ln.decode('utf-8')[:-1])
		
		print("wait")
		await child.wait()
	
	def some_work_1():
		z = 0
		for m in range(10):
			print("some_work_1", m, z)
			for n in range(100000):
				z ^= z >> 5 + z << 3
				z ^= n ** 2
				z %= 999997
		return z
	
	def some_work_2():
		z = 1
		for m in range(10):
			print("some_work_2", m, z)
			for n in range(100000):
				z ^= z >> 6 + z << 4
				z ^= n ** 2
				z %= 999993
		return z
	
	async def test_executors():
		a = get_running_loop().run_in_executor(None, some_work_1)
		b = get_running_loop().run_in_executor(None, some_work_2)
		ab = await gather(a, b)
		assert ab == [285292, 591580], str(ab)
	
	async def test_A_prim():
		print("test_A_prim")
	
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
		await test_A_prim()
		print("testA", 7)
		await sleep(0.2)
		await e
		#return "a", a
		return "a", a
	
	async def testB():
		async with Connection1('http://www.google.com/') as google:
			first_line = (await google.Url().get())[:32]
			assert first_line == b'<!doctype html><html itemscope="', first_line
		
		async with Connection1('https://github.com/') as github:
			first_line = (await github.Url().get())[:32]
			assert first_line == b'\n\n\n\n\n\n\n<!DOCTYPE html>\n<html\n  l', first_line
		
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
	
	async def test_pipes():
		from os import pipe, set_blocking, fdopen, close
		from asyncio import StreamReaderProtocol
		from asyncio.streams import FlowControlMixin
		
		read_fd_in, write_fd_in = pipe()
		read_fd_out, write_fd_out = pipe()
		set_blocking(write_fd_in, False)
		set_blocking(read_fd_out, False)
		
		loop = get_running_loop()
		print("spawning slave")
		slave = await create_subprocess_exec(__file__, '--test-pipes', str(read_fd_in), str(write_fd_out), stdin=PIPE, pass_fds=(read_fd_in, write_fd_out))
		
		reader = StreamReader(loop=loop)
		r_transport, r_protocol = await loop.connect_read_pipe(lambda: SubprocessTransport.ReaderProtocol(read_fd_out, slave._transport), Gio.UnixInputStream.new(read_fd_out, True))
		reader.set_transport(r_transport)
		r_protocol._stream_reader = reader
		
		w_transport, w_protocol = await loop.connect_write_pipe(lambda: SubprocessTransport.WriterProtocol(write_fd_in, slave._transport), Gio.UnixOutputStream.new(write_fd_in, True))
		writer = StreamWriter(w_transport, w_protocol, reader, loop)
		w_protocol._stream_writer = writer
		
		await r_transport.start()
		await w_transport.start()
		
		await slave.stdin.drain()
		
		await writer.drain()
		writer.write(b"123456789........................!")
		await sleep(1)
		writer.write(b"abcdefgh.........................!")
		await sleep(1)
		writer.write_eof()
		
		print("reading...")
		print("read:", await reader.readline())
		
		print("closing")
		writer.close()
		print("closed")
		
		await slave.wait()
		print("done")
	
	async def test():
		#await test_pipes()
		await test_process()
		await test_executors()
		await testA()
		return 'a'
	
	a = run(test())
	assert a == 'a', a


