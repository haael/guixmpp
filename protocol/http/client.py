#!/usr/bin/python3


from asyncio import get_running_loop, Event, Lock
from collections import deque

import h11
import h2.connection
import ssl


class ResolveError(Exception):
	pass


class HTTPError(Exception):
	pass


class Connection:
	"HTTP/1.1 connection"
	
	def __init__(self, baseurl):
		self.baseurl = baseurl
		
		self.protocol, _, self.host, *path = baseurl.split('/')
		self.path = '/'.join(path)
		
		if ':' in self.host:
			self.host, port = self.host.split(':')
			self.port = int(port)
		else:
			self.port = 80 if (self.protocol == 'http:') else 443 if (self.protocol == 'https:') else None
		
		if not 0 < self.port < 65536:
			raise ValueError("Port needs to be in range 1...65535.")
		
		if self.protocol == 'http:':
			self.ssl_context = None
		elif self.protocol == 'https:':
			self.ssl_context = self.create_ssl_context()
		else:
			raise ValueError(f"Protocol {self.protocol} not supported.")
		
		self.headers = {}
		self.headers['user-agent'] = 'guixmpp'
		self.headers['connection'] = 'keep-alive'
	
	def create_ssl_context(self):
		raise NotImplementedError
	
	def connection_made(self, transport):
		#print('connection_made', transport)
		self.__transport = transport
	
	def connection_lost(self, exc):
		#print('connection_lost', exc)
		
		del self.__transport
		
		if exc:
			raise exc # TODO: raise proper exception
	
	def data_received(self, data):
		self.__arrived.set()
	
	async def send_data(self, data):
		#print('send_data')
		await self.__writing.wait()
		self.__transport.write(data)
	
	async def wait_for_data(self):
		await self.__arrived.wait()
		self.__arrived.clear()
	
	def start_body_reception(self):
		self.__eof = False
	
	def eof_received(self):
		self.__eof = True
	
	def is_eof(self):
		return self.__eof
	
	def pause_writing(self):
		self.__writing.clear()
	
	def resume_writing(self):
		self.__writing.set()
	
	async def open(self):
		if hasattr(self, 'loop'):
			raise ValueError("Already opened.")
		
		self.loop = get_running_loop()
		self.__writing = Event()
		self.__arrived = Event()
		self.__eof = True
		
		errors = []
		for family, type_, proto, cname, addr_port in await self.loop.getaddrinfo(self.host, self.port):
			host = addr_port[0]
			port = addr_port[1]
			try:
				await self.loop.create_connection((lambda: self), host, port, family=family, proto=proto, server_hostname=self.host if self.ssl_context else None, ssl=self.ssl_context)
				self.__writing.set()
			except Exception as error:
				errors.append(error)
			else:
				return
		else:
			if len(errors) == 0:
				raise ResolveError(f"Could not resolve host name {self.host} (port {self.port}).")
			else:
				raise ExceptionGroup("Could not connect to server.", errors)
	
	async def close(self):
		if not hasattr(self, 'loop'):
			raise ValueError("Already closed.")
		
		try:
			self.__transport.close()
		except AttributeError: # error before connection established
			pass
		
		del self.loop, self.__writing, self.__arrived, self.__eof
	
	def begin_stream(self):
		raise NotImplementedError
	
	def end_stream(self, stream):
		raise NotImplementedError
	
	async def send_request(self, stream, method, path, headers):
		raise NotImplementedError
	
	async def write(self, stream, data):
		raise NotImplementedError
	
	async def response(self, stream):
		raise NotImplementedError
	
	async def read(self, stream, bufsize):
		raise NotImplementedError
		
	async def __aenter__(self):
		await self.open()
		return self
	
	async def __aexit__(self, *args):
		await self.close()
	
	def Url(self, relurl='', headers={}):
		return Url(relurl, dict(headers), self)


class Connection1(Connection):
	"HTTP/1.1 connection"
	
	def __init__(self, *args):
		super().__init__(*args)
		self.__lock = Lock()
	
	async def begin_stream(self):
		await self.__lock.acquire()
		return 0
	
	async def end_stream(self, stream):
		self.__lock.release()
	
	def create_ssl_context(self):
		return ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH) # client connection should have purpose=ssl.Purpose.SERVER_AUTH
	
	def data_received(self, data):
		self.__http.receive_data(data)
		super().data_received(data)
	
	async def send_request(self, stream, method, path, headers):
		self.read_buffer = deque()
		self.__http = h11.Connection(our_role=h11.CLIENT)
		data = self.__http.send(h11.Request(method=method, target=path, headers=list(headers.items())))
		await self.send_data(data)
	
	async def write(self, stream, data):
		data = self.__http.send(h11.Data(data=data))
		await self.send_data(data)
	
	async def response(self, stream):
		data = self.__http.send(h11.EndOfMessage())
		await self.send_data(data)
		
		event = self.__http.next_event()
		while event is h11.NEED_DATA:
			await self.wait_for_data()
			event = self.__http.next_event()
		
		assert type(event) is h11.Response
		
		self.start_body_reception()
		
		headers = dict((_key.decode('ascii'), _value.decode('ascii')) for (_key, _value) in event.headers)
		return event.status_code, headers
	
	async def read(self, stream, bufsize):
		if bufsize is not None and bufsize <= 0:
			raise ValueError("`bufsize` must be > 0")
		
		if self.is_eof() and not self.read_buffer:
			return bytes()
		
		result = []
		
		while (bufsize is None) or sum(len(_chunk) for _chunk in result) < bufsize:
			try:
				chunk = self.read_buffer.popleft()
			except IndexError:
				break
			else:
				if bufsize is None:
					result.append(chunk)
				else:
					needed = bufsize - sum(len(_chunk) for _chunk in result)
					if len(chunk) <= needed:
						result.append(chunk)
					else:
						result.append(chunk[:needed])
						self.read_buffer.insert(0, chunk[needed:])
		
		if not self.is_eof():
			while (bufsize is None) or sum(len(_chunk) for _chunk in result) < bufsize:
				event = self.__http.next_event()
				while event is h11.NEED_DATA:
					await self.wait_for_data()
					event = self.__http.next_event()
				
				if type(event) is h11.Data:
					if bufsize is None:
						result.append(event.data)
					else:
						needed = bufsize - sum(len(_chunk) for _chunk in result)
						chunk = event.data
						if len(chunk) <= needed:
							result.append(chunk)
						else:
							result.append(chunk[:needed])
							self.read_buffer.append(chunk[needed:])
				elif type(event) is h11.EndOfMessage:
					self.eof_received()
					break
		
		return bytes().join(result)


class Connection2(Connection):
	"HTTP/2 connection"
	
	def __init__(self, *args):
		super().__init__(*args)
		self.__locks = {}
		self.__streams = 0
	
	async def begin_stream(self):
		stream = self.__streams
		self.__streams += 1
		lock = self.__locks[stream] = Lock()
		await lock.acquire()
		return stream
	
	async def end_stream(self, stream):
		self.__locks[stream].release()
		del self.__locks[stream]
	
	def create_ssl_context(self):
		ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH) # client connection should have purpose=ssl.Purpose.SERVER_AUTH
		ctx.set_alpn_protocols(['h2'])
		return ctx
	
	def data_received(self, data):
		events = self.__http.receive_data(data)
		self.__events.extend(events)
		super().data_received(data)
	
	async def send_request(self, stream, method, path, headers):
		self.__read_buffer = deque()
		conn = self.__http = h2.connection.H2Connection()
		conn.initiate_connection()
		await self.send_data(conn.data_to_send())
		
		headers = [
			(':method', method),
			(':path', path),
			(':authority', self.host),
			(':scheme', self.protocol[:-1])
		]
		conn.send_headers(1, headers, end_stream=True)
		await self.send_data(conn.data_to_send())
	
	async def write(self, stream, data):
		data = self.__http.send(h2.Data(data=data))
		await self.send_data(data)
	
	async def response(self, stream):



		data = self.__http.send(h2.EndOfMessage())
		await self.send_data(data)
		
		event = self.__http.next_event()
		while event is h2.NEED_DATA:
			await self.wait_for_data()
			event = self.http.next_event()
		
		assert type(event) is h2.Response
		
		self.start_body_reception()
		
		headers = dict((_key.decode('ascii'), _value.decode('ascii')) for (_key, _value) in event.headers)
		return event.status_code, headers
	
	async def read(self, stream, bufsize):
		if bufsize is not None and bufsize < 0:
			raise ValueError
		
		if self.is_eof() and not self.read_buffer:
			return bytes()
		
		result = []
		
		while (bufsize is None) or sum(len(_chunk) for _chunk in result) < bufsize:
			try:
				chunk = self.read_buffer.popleft()
			except IndexError:
				break
			else:
				if bufsize is None:
					result.append(chunk)
				else:
					needed = bufsize - sum(len(_chunk) for _chunk in result)
					if len(chunk) <= needed:
						result.append(chunk)
					else:
						result.append(chunk[:needed])
						self.read_buffer.insert(0, chunk[needed:])
		
		while (not self.is_eof()) and ((bufsize is None) or sum(len(_chunk) for _chunk in result) < bufsize):
			for event in events:
				if isinstance(event, h2.events.DataReceived):
					self.__http.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
					chunk = event.data
					
					if bufsize is None:
						result.append(chunk)
					else:
						needed = bufsize - sum(len(_chunk) for _chunk in result)
						if len(chunk) <= needed:
							result.append(chunk)
						else:
							result.append(chunk[:needed])
							self.read_buffer.insert(0, chunk[needed:])
				
				elif isinstance(event, h2.events.StreamEnded):
					self.eof_received()
					break
			if not self.is_eof():
				self.send_data(self.__http.data_to_send())
				await self.wait_for_data()
		
		return bytes().join(result)


class Url:
	def __init__(self, path, headers, client):
		self.path = path
		self.client = client
		self.headers = headers
	
	@property
	def abspath(self):
		if self.path.startswith('/'):
			return self.path
		elif self.client.path.endswith('/'):
			return self.client.path + self.path
		else:
			return self.client.path + '/' + self.path
	
	def build_headers(self, headers, content_length=None):
		h = dict()
		h.update(self.client.headers)
		h.update(self.headers)
		h.update(headers)
		h['host'] = self.client.host
		if content_length is not None:
			h['content-length'] = int(content_length)
		return h
	
	def get(self, *, headers={}):
		return Request(self.client, self.abspath, 'GET', False, None, self.build_headers(headers), False)
	
	def head(self, *, headers={}):
		return Request(self.client, self.abspath, 'HEAD', False, None, self.build_headers(headers), True)
	
	def post(self, *, body=None, headers={}):
		return Request(self.client, self.abspath, 'POST', True, body, self.build_headers(headers, len(body) if body is not None else None), False)
	
	def put(self, *, body=None, headers={}):
		return Request(self.client, self.abspath, 'PUT', True, body, self.build_headers(headers, len(body) if body is not None else None), False)
	
	def delete(self, *, headers={}):
		return Request(self.client, self.abspath, 'DELETE', False, None, self.build_headers(headers), False)
	
	def options(self):
		...
	
	def trace(self):
		...
	
	def patch(self):
		...
	
	# DAV methods
	
	def copy(self):
		...
	
	def lock(self):
		...
	
	def mkcol(self):
		...
	
	def move(self):
		...
	
	def propfind(self):
		...
	
	def proppatch(self):
		...
	
	def unlock(self):
		...


class Request:
	def __init__(self, client, path, method, writable, body, headers, return_headers):
		self.client = client
		self.path = path
		self.method = method
		self.closed = False
		self.__writable = writable
		self.chunk_size = 4096
		self.body = body
		self.headers = headers
		self.request_sent = False
		self.return_headers = return_headers
	
	def __await__(self):
		result = None
		
		async def execute():
			nonlocal result
			
			async with self:
				status, headers = await self.response()
				if self.return_headers:
					result = status, headers
				else:
					self.raise_for_status(status)
					result = await self.read()
		
		yield from self.client.loop.create_task(execute())
		return result
	
	async def open(self):
		self.stream = await self.client.begin_stream()
		if self.body is not None:
			await self.write(body)
	
	async def close(self):
		await self.client.end_stream(self.stream)
		self.closed = True
		del self.stream
	
	async def __aenter__(self):
		await self.open()
		return self
	
	async def __aexit__(self, *args):
		await self.close()
	
	async def response(self):
		if not self.request_sent:
			await self.client.send_request(self.stream, self.method, self.path, self.headers)
		else:
			raise ValueError
		return await self.client.response(self.stream)
	
	def raise_for_status(self, status):
		if 100 <= status <= 399:
			pass
		elif 400 <= status <= 599:
			raise HTTPError(f"HTTP error {status}.", status)
	
	async def read(self, bufsize=None):
		if bufsize is not None:
			return await self.client.read(self.stream, bufsize)
		else:
			return bytes().join(await self.readchunks())
	
	async def readchunks(self):
		result = []
		async for chunk in self:
			result.append(chunk)
		return result
	
	async def __aiter__(self):
		chunk = await self.client.read(self.stream, self.chunk_size)
		while chunk:
			yield chunk
			chunk = await self.client.read(self.stream, self.chunk_size)
	
	async def write(self, data):
		if not self.writable():
			raise ValueError
		
		if not self.request_sent:
			await self.client.send_request(self.stream, self.method, self.path, self.headers)
			self.request_sent = True
		
		await self.client.write(self.stream, data)
	
	async def writelines(self, chunks):
		if not self.writable():
			raise ValueError
		for chunk in chunks:
			await self.write(chunk)
	
	async def copy(self, source):
		if not self.writable():
			raise ValueError
		async for chunk in source:
			await self.write(chunk)
	
	def writable(self):
		return self.__writable
	
	def seekable(self):
		return False


if __debug__ and __name__ == '__main__':
	from asyncio import run, sleep
	
	async def main():
		async with Connection2('https://www.google.com/') as google:
			print(await google.Url().get())
			print()
			
			print(await google.Url('sitemap.xml').get())
			print()
			
			print(await google.Url('robotz.txt').head())
			print()
			
			print(await google.Url('robots.txt').head())
			print()
	
	run(main())


