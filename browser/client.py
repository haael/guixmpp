#!/usr/bin/python3

from logging import getLogger
logger = getLogger(__name__)

from asyncio import open_connection, wait_for, create_task, Lock, CancelledError, Queue, get_running_loop, gather
from ssl import create_default_context
from lxml.etree import fromstring, tostring, XMLPullParser
from scramp import ScramClient, ScramMechanism
from base64 import b64encode, b64decode
from secrets import token_urlsafe
from collections import Counter, deque


class ProtocolError(Exception):
	pass


class StreamError(Exception):
	pass


class AuthenticationError(Exception):
	pass


class QueryError(Exception):
	pass


class XMPPClient:
	def __init__(self, jid, password=None):
		self.jid = jid
		self.password = password
		self.register = False
		
		self.established = False
		self.encrypted = False
		self.authenticated = False
		self.running = False
		
		self.read_lock = Lock()
		self.write_lock = Lock()
		self.interrupt_message = None
		
		self.iq_requests = {}
		self.tasks = TaskWatch()
		self.unhandled = False
		self.handlers_running = Counter()
		self.expectations = []
		
		self.recv_stanza_counter = 0
		self.sent_stanza_counter = 0
		self.saved_stanzas = {}
		
		self.config = {
			'ping': True
		}
	
	async def connect(self, host=None, port=None, ssl=False, timeout=None):		
		if not host: host = self.jid.split('@')[1].split('/')[0]
		if not port: port = 5223 if ssl else 5222
		
		logger.info(f"Connecting to XMPP server {host}:{port}, ssl={ssl}.")
		
		if not timeout:
			self.reader, self.writer = await open_connection(host, port, ssl=ssl)
		else:
			self.reader, self.writer = await wait_for(open_connection(host, port, ssl=ssl), timeout)
		
		self.encrypted = bool(ssl)
	
	async def disconnect(self):
		logger.info("Disconnecting from XMPP server.")
		self.writer.close()
		await self.writer.wait_closed()
		del self.reader, self.writer
	
	async def starttls(self, ssl=None, timeout=None, host=None):
		async with (self.read_lock, self.write_lock):
			self.established = False
		
		assert not hasattr(self, 'read_task')
		
		logger.info("Upgrading transport to TLS.")
		
		if not host: host = self.jid.split('@')[1].split('/')[0]
		if not ssl: ssl = create_default_context()
		
		#await self.writer.start_tls(ssl, server_hostname=host, ssl_handshake_timeout=timeout)
		#self.reader._transport = self.writer.
		
		loop = get_running_loop()
		transport = self.writer.transport
		protocol = transport.get_protocol()
		
		if not timeout:
			new_transport = await loop.start_tls(transport, protocol, ssl)
		else:
			new_transport = await wait_for(loop.start_tls(transport, protocol, ssl), timeout)
		
		# Replace the writers
		self.writer._transport = new_transport
		self.reader._transport = new_transport
		
		self.encrypted = True
	
	async def begin_stream(self, bare_jid=None, server=None):
		async with (self.read_lock, self.write_lock):
			logger.info("Begin XMPP stream.")
			
			self.parser = XMLPullParser(events=['start', 'end'])
			
			if not bare_jid: bare_jid = self.jid.split('/')[0]
			if not server: server = self.jid.split('@')[1].split('/')[0]
			
			data = f'<?xml version="1.0"?><stream:stream from="{bare_jid}" to="{server}" version="1.0" xmlns="jabber:client" xmlns:stream="http://etherx.jabber.org/streams">'.encode('utf-8')
			self.writer.write(data)
			await self.writer.drain()
			
			stream_tag = False
			while not stream_tag:
				data = await self.reader.readuntil(b'>')
				self.parser.feed(data)
				for event, element in self.parser.read_events():
					if event == 'start' and element.tag == '{http://etherx.jabber.org/streams}stream':
						stream_tag = True
					else:
						logger.error(f"Received unexpected tag: {element.tag}")
						raise ProtocolError("Expected <stream> opening tag.")
			
			self.established = True
			self.authenticated = False
	
	async def end_stream(self):
		async with self.write_lock:
			logger.info("End XMPP stream.")
			
			self.writer.write(b'</stream:stream>')
			await self.writer.drain()
			
			if self.established:
				logger.info("Waiting for end tag...")
			while True:
				if await self.recv_stanza() == None:
					break
			
			self.established = False
			self.authenticated = False
			del self.parser
	
	async def send_stanza(self, stanza):
		async with self.write_lock:
			if not self.established:
				raise StreamError("Stream closed.")
			self.writer.write(tostring(stanza))
			logger.debug(f"sending stanza:  {tostring(stanza).decode('utf-8')}")
			await self.writer.drain()
	
	async def recv_stanza(self):
		async with self.read_lock:
			stanza_received = False
			while not stanza_received:
				self.read_task = create_task(self.reader.readuntil(b'>'))
				try:
					data = await self.read_task
				except CancelledError:
					return ...
				finally:
					del self.read_task
				
				self.parser.feed(data)
				for event, element in self.parser.read_events():
					if event == 'end':
						if element.tag == '{http://etherx.jabber.org/streams}stream' and element.getparent() == None:
							logger.debug(f"Received stream end tag.")
							return None
						elif element.getparent().tag == '{http://etherx.jabber.org/streams}stream' and element.getparent().getparent() == None:
							logger.debug(f"received stanza: {tostring(element).decode('utf-8')}.")
							return element
	
	async def __aenter__(self):
		await self.connect()
		await self.begin_stream()
		return self
	
	async def __aiter__(self):
		if self.running:
			raise ValueError("Client already running.")
		
		self.running = True
		logger.info("Client stanza reception loop running.")
		while self.running:			
			stanza = await self.recv_stanza()
			if stanza == None:
				logger.warning("Received end tag from remote server.")
				self.established = False
				break
			elif stanza == Ellipsis:
				logger.info(f"Received loop interrupt request.")
				if self.interrupt_message:
					yield self.interrupt_message
					self.interrupt_message = None
					continue
				else:
					break
			else:
				yield stanza
			
			self.handlers_running = +self.handlers_running
			if self.handlers_running:
				save_from = min(self.handlers_running.keys())
				for to_delete in [_serial for _serial in self.saved_stanzas.keys() if _serial < save_from]:
					del self.saved_stanzas[to_delete]
				self.saved_stanzas[self.recv_stanza_counter] = stanza
			else:
				self.saved_stanzas.clear()
			
			if self.unhandled:
				await self.on_unhandled(stanza)
			
			errors = self.tasks.errors()
			if errors:
				client.stop()
				self.tasks.cancel()
				await self.tasks.wait() # FIXME: ignore cancellation exceptions
				errors.extend(self.tasks.errors())
				raise ExceptionGroup("Errors in background tasks.", errors)
			
			self.recv_stanza_counter += 1
		
		errors = self.tasks.errors()
		self.tasks.cancel()
		await self.tasks.wait() # FIXME: ignore cancellation exceptions
		errors.extend(self.tasks.errors())
		if errors:
			raise ExceptionGroup("Errors in background tasks.", errors)
		
		logger.info("Client stanza reception loop stopped.")
		self.running = False
	
	async def __aexit__(self, exception, messagge, traceback):
		if exception:
			logger.warning(f"Exit context manager due to exception: <{exception}> {messagge}.")
		await self.end_stream()
		await self.disconnect()
	
	def stop(self):
		self.running = False
		if hasattr(self, 'read_task'):
			self.read_task.cancel()
	
	async def on_stanza(self, stanza):
		result = None
		
		if stanza.tag == '{http://etherx.jabber.org/streams}features':
			result = await self.on_features(stanza)
		elif stanza.tag == '{jabber:client}iq':
			result = await self.on_iq(stanza)
		elif stanza.tag == '{jabber:client}message':
			result = await self.on_message(stanza)
		elif stanza.tag == '{jabber:client}presence':
			result = await self.on_presence(stanza)
		else:
			logger.warning(f"Received unknown stanza: {tostring(stanza).decode('utf-8')}")
		
		for match_, queue in self.expectations:
			is_match = False
			
			if result:
				try:
					is_match = match_(*result)
				except (TypeError, IndexError, AttributeError):
					is_match = False
				
				if is_match:
					single = False
			
			if not is_match:
				try:
					is_match = match_(stanza)
				except (TypeError, IndexError, AttributeError):
					is_match = False
				
				if is_match:
					single = True
			
			if is_match:
				if single:
					await queue.put(stanza)
				elif result:
					await queue.put(result)
		
		return result
	
	async def on_features(self, stanza):
		if stanza.tag != '{http://etherx.jabber.org/streams}features':
			raise ValueError
		
		logger.info("Processing stream features.")
		for feature in stanza:
			logger.debug(f" feature: {feature.tag}")
		
		tasks = []
		interrupt = False
		result = None
		for feature in stanza:
			if feature.tag == '{urn:ietf:params:xml:ns:xmpp-tls}starttls':
				interrupt = await self.on_starttls(feature)
			elif feature.tag == '{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms':
				interrupt = await self.on_authenticate(feature)
			elif feature.tag == '{http://jabber.org/features/iq-register}register':
				result = await self.on_register(feature)
				interrupt = bool(result)
			elif feature.tag == '{urn:ietf:params:xml:ns:xmpp-bind}bind':
				tasks.append(self.on_bind(feature))
			#else:
			#	logger.warning(f"Unsupported feature: {feature.tag}.")
			
			if interrupt or not self.established:
				break
		
		if tasks:
			async def run_tasks():
				for task in tasks:
					await task
				await self.ready()
			
			self.tasks.add(self.guarded(run_tasks()), name='on_features')
		
		return result
	
	async def on_starttls(self, feature):
		if feature.tag != '{urn:ietf:params:xml:ns:xmpp-tls}starttls':
			raise ValueError
		
		logger.info("Initiating STARTTLS procedure.")
		await self.send_stanza(fromstring(b'<starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"/>'))
		stanza = await self.recv_stanza()
		if stanza.tag != '{urn:ietf:params:xml:ns:xmpp-tls}proceed':
			raise ProtocolError("Expected starttls proceed stanza.")
		await self.starttls()
		await self.begin_stream()
		return True
	
	async def on_authenticate(self, feature):
		if feature.tag != '{urn:ietf:params:xml:ns:xmpp-sasl}mechanisms':
			raise ValueError
		
		mechanisms = [_mechanism.text for _mechanism in feature]
		
		password = await self.get_password(self.jid, ('ANONYMOUS' in mechanisms))
		if password == None:
			logger.info("Not attempting login.")
			return False
		
		if password:
			logger.info("Authenticating on the server.")
			supported_mechanisms = list(ScramMechanism.MECH_LOOKUP.keys())
			available_mechanisms = [_mechanism for _mechanism in supported_mechanisms if _mechanism in mechanisms]
		else:
			logger.info("Trying anonymous login.")
			supported_mechanisms = ['ANONYMOUS']
			available_mechanisms = [_mechanism for _mechanism in supported_mechanisms if _mechanism in mechanisms]
		
		logger.debug(f" server supported mechanisms: {mechanisms}")
		logger.debug(f" client supported mechanisms: {supported_mechanisms}")
		logger.debug(f"        available mechanisms: {available_mechanisms}")
		
		if not available_mechanisms:
			logger.error("No supported authentication mechanism found.")
			raise AuthenticationError("No supported authentication mechanism found.")
		
		if password:
			scram = ScramClient(available_mechanisms, self.jid.split('@')[0], password)
			logger.debug(f"Chosen SASL mechanism: {scram.mechanism_name}")
			
			message = scram.get_client_first()
			logger.debug(f"Client auth: {message}")
			await self.send_stanza(fromstring(f'<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="{scram.mechanism_name}">{b64encode(message.encode("utf-8")).decode("utf-8")}</auth>'.encode('utf-8')))
			
			stanza = await self.recv_stanza()
			if stanza.tag == '{urn:ietf:params:xml:ns:xmpp-sasl}failure':
				try:
					status = "Unauthorized: " + [_child.text for _child in stanza if _child.tag == '{urn:ietf:params:xml:ns:xmpp-sasl}text'][0]
				except (IndexError, TypeError):
					status = "Unauthorized."
				raise AuthenticationError(status)
			if stanza.tag != '{urn:ietf:params:xml:ns:xmpp-sasl}challenge':
				raise ProtocolError("Expected SASL challenge.")
			message = b64decode(stanza.text).decode("utf-8")
			logger.debug(f"Server challenge: {message}")
			scram.set_server_first(message)
			
			message = scram.get_client_final()
			logger.debug(f"Client response: {message}")
			await self.send_stanza(fromstring(f'<response xmlns="urn:ietf:params:xml:ns:xmpp-sasl">{b64encode(message.encode("utf-8")).decode("utf-8")}</response>'.encode('utf-8')))
			
			stanza = await self.recv_stanza()
			if stanza.tag == '{urn:ietf:params:xml:ns:xmpp-sasl}failure':
				try:
					status = "Unauthorized: " + [_child.text for _child in stanza if _child.tag == '{urn:ietf:params:xml:ns:xmpp-sasl}text'][0]
				except (IndexError, TypeError):
					status = "Unauthorized."
				raise AuthenticationError(status)
			if stanza.tag != '{urn:ietf:params:xml:ns:xmpp-sasl}success':
				raise ProtocolError("Expected SASL challenge.")
			message = b64decode(stanza.text).decode("utf-8")
			logger.debug(f"Server result: {message}")
			scram.set_server_final(message)
		
		else:
			raise NotImplementedError
		
		logger.info("Authorized.")
		await self.begin_stream()
		self.authenticated = True
		return True
	
	async def on_register(self, feature):
		if self.register:
			logger.info("Attempting account registration.")
			return 'register'
	
	async def on_bind(self, feature):
		resource = self.jid.split('/')[1]
		
		stanza, = await self.query('set', None, fromstring(f'<bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><resource>{resource}</resource></bind>'.encode('utf-8')))
		if stanza.tag != '{urn:ietf:params:xml:ns:xmpp-bind}bind':
			raise ProtocolError("Unable to bind resource: unexpected response tag.")
		
		try:
			jid = [_child.text for _child in stanza if _child.tag == '{urn:ietf:params:xml:ns:xmpp-bind}jid'][0]
		except IndexError:
			raise ProtocolError("Unable to bind resource: JID not found in server response.")
		
		logger.info(f"Bound resource: {jid}")
		
		self.jid = jid
	
	async def on_presence(self, stanza):
		id_ = stanza.attrib.get('id', None)
		from_ = stanza.attrib.get('from', None)
		body = []
		
		if stanza.text and stanza.text.strip():
			body.append(stanza.text.strip())
		
		for child in stanza:
			if child.tail and child.tail.strip():
				text = child.tail.strip()
			else:
				text = None
			
			child.tail = None
			body.append(child)
			if text is not None:
				body.append(text)
		
		return 'presence', id_, from_, *body
	
	async def on_message(self, stanza):
		id_ = stanza.attrib.get('id', None)
		from_ = stanza.attrib.get('from', None)
		body = []
		
		if stanza.text and stanza.text.strip():
			body.append(stanza.text.strip())
		
		for child in stanza:
			if child.tail and child.tail.strip():
				text = child.tail.strip()
			else:
				text = None
			
			child.tail = None
			body.append(child)
			if text is not None:
				body.append(text)
		
		return 'message', id_, from_, *body
	
	async def on_iq(self, stanza):
		logger.debug(f"Received IQ stanza: {tostring(stanza).decode('utf-8')}")
		
		id_ = stanza.attrib.get('id', None)
		method = stanza.attrib['type']		
		if method in ('result', 'error'):
			if id_ in self.iq_requests:
				self.iq_requests[id_].set_result(stanza)
			else:
				raise ProtocolError("Unexpected response for IQ that wasn't requested.")
		elif method in ('get', 'set'):
			body = []
			
			if stanza.text and stanza.text.strip():
				body.append(stanza.text.strip())
			
			for child in stanza:
				if child.tail and child.tail.strip():
					text = child.tail.strip()
				else:
					text = None
				
				child.tail = None
				body.append(child)
				if text is not None:
					body.append(text)
			
			from_ = stanza.attrib.get('from', None)
			return await self.on_query(method, id_, from_, *body)
		else:
			raise ProtocolError(f"Unsupported method {method} in IQ.")
	
	async def on_unhandled(self, stanza):
		if stanza.tag == '{jabber:client}iq':
			logger.warning(f"Unhandled iq: {tostring(stanza).decode('utf-8')}")
			await self.answer('error', stanza.attrib['id_'], stanza.attrib['from_'], fromstring(b'<error type="cancel"><service-unavailable xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/></error>'))
		elif stanza.tag == '{jabber:client}message':
			pass
		self.unhandled = False
	
	async def on_query(self, method, id_, from_, *body):
		if self.config['ping'] and len(body) == 1 and hasattr(body[0], 'tag') and body[0].tag == '{urn:xmpp:ping}ping':
			logger.info(f"Ping from {from_}.")
			await self.answer('result', id_, from_)
		else:
			return await self.on_other_query(method, id_, from_, *body)
	
	async def on_other_query(self, method, id_, from_, *body):
		self.unhandled = True
		return 'iq.' + method, id_, from_, *body
	
	def random_token(self):
		return token_urlsafe(6)
	
	async def query(self, method, to, *body, timeout=10):
		if method not in ('get', 'set'):
			raise ValueError
		
		if not (isinstance(to, str) or to == None):
			raise ValueError
		
		id_ = self.random_token()
		if to:
			# TODO: validate jid
			iq = fromstring(f'<iq id="{id_}" type="{method}" to="{to}"/>'.encode('utf-8'))
		else:
			iq = fromstring(f'<iq id="{id_}" type="{method}"/>'.encode('utf-8'))
		
		prev = None
		for item in body:
			if isinstance(item, str):
				if prev:
					if prev.tail:
						prev.tail += item
					else:
						prev.tail = item
				else:
					if iq.text:
						iq.text += item
					else:
						iq.text = item
			else:
				iq.append(item)
				prev = item
		
		response = get_running_loop().create_future()
		self.iq_requests[id_] = response
		
		await self.send_stanza(iq)
		
		try:
			if not timeout:
				result = await response
			else:
				result = await wait_for(response, timeout)
		finally:
			del self.iq_requests[id_]
		
		if result.attrib['type'] == 'result':
			return list(result)
		elif result.attrib['type'] == 'error':
			try:
				msg = tostring([_error for _error in result if _error.tag == '{jabber:client}error'][0][0]).decode('utf-8')
			except IndexError:
				msg = ""
			raise QueryError(f"Server error on iq {method} (id:{id_}, to:{to}): {msg}", list(result))
		else:
			raise ProtocolError
	
	async def answer(self, id_, method, to, *body):
		if method not in ('result', 'error'):
			raise ValueError
		
		if not id_:
			raise ValueError
		
		iq = fromstring(f'<iq id="{id_}" type="{method}" to="{to}"/>'.encode('utf-8'))
		
		prev = None
		for item in body:
			if isinstance(item, str):
				if prev:
					if prev.tail:
						prev.tail += item
					else:
						prev.tail = item
				else:
					if iq.text:
						iq.text += item
					else:
						iq.text = item
			else:
				iq.append(item)
				prev = item
		
		await self.send_stanza(iq)
	
	async def get_password(self, jid, anonymous_ok):
		return self.password
	
	async def ready(self):
		logger.info("Initialization complete, stream ready.")
		self.interrupt_message = 'ready'
		if hasattr(self, 'read_task'):
			self.read_task.cancel()
	
	async def guarded(self, coro):
		try:
			return await coro
		except:
			self.interrupt_message = 'exception'
			if hasattr(self, 'read_task'):
				self.read_task.cancel()
			raise
	
	def handle(self, coro):
		self.handled = True
		stanza_serial = self.recv_stanza_counter
		self.handlers_running[stanza_serial] += 1
		queue = Queue()
		
		async def expect(match_):
			return await self.expect(queue, match_)
		
		async def handler(coro):
			try:
				await coro(expect)
			finally:
				self.handlers_running[stanza_serial] -= 1
		
		for serial, stanza in sorted([(_serial, _stanza) for (_serial, _stanza) in self.saved_stanzas.items()], key=lambda _item: _item[0]):
			queue.put_nowait(stanza)
		
		self.tasks.add(self.guarded(handler(coro)), coro.__name__)
	
	async def expect(self, queue, match_):
		self.expectations.append((match_, queue))
		try:
			return await queue.get()
		finally:
			self.expectations.remove((match_, queue))


class TaskWatch:
	def __init__(self):
		self.tasks = []
	
	def add(self, coro, name=None):
		self.tasks.append(create_task(coro, name=name))
	
	def errors(self):
		errors = []
		
		for task in self.tasks[:]:
			if not task.done():
				continue
			
			self.tasks.remove(task)
			
			if task.cancelled():
				pass
			elif task.exception():
				errors.append(task.exception())
		
		return errors
	
	def cancel(self):
		for task in self.tasks[:]:
			task.cancel()
	
	async def wait(self):
		for task in self.tasks[:]:
			try:
				await task
			except CancelledError:
				pass


if __name__ == '__main__':
	from logging import DEBUG, StreamHandler
	logger.setLevel(DEBUG)
	logger.addHandler(StreamHandler())
	
	from asyncio import run
	
	async def main():
		async with XMPPClient('haael@dw.live/discovery') as client:
			#client.password = ''
			
			async for stanza in client:
				if hasattr(stanza, 'tag'):
					event = await client.on_stanza(stanza)
				else:
					event = stanza
				type_ = None
				logger.debug(f"Main loop event: {event}.")
				
				if not event:
					continue
				
				elif event == 'ready':
					if not client.authenticated or not client.established:
						break
					@client.handle
					async def get_roster(expect):
						roster, = await client.query('get', None, fromstring(b'<query xmlns="jabber:iq:roster"/>'))
						for item in roster:
							print("roster item:", tostring(item))
						client.stop()
				
				elif event == 'register':
					@client.handle
					async def register(expect):
						reg_query, = await client.query('get', None, fromstring(b'<query xmlns="jabber:iq:register"/>'))
						for child in reg_query:
							print("registration field:", tostring(child))
						client.stop()
				
				elif isinstance(event, str):
					logger.warning(f"Ignored event: {event}")
					continue
				
				else:
					type_, id_, from_, *elements = event
				
				
				if type_ == None:
					continue
				
				elif type_ == 'iq.get' and len(elements) == 1 and hasattr(elements[0], 'tag') and elements[0].tag == '{boom}boom':
					await client.answer('result', id_, from_, "boom")
					client.unhandled = False
				
				elif type_ == 'iq.set' and len(elements) == 1 and hasattr(elements[0], 'tag') and elements[0].tag == '{boom}boom':
					@client.handle
					async def boom_get(expect, type_=type_, id_=id_, from_=from_, elements=elements):
						try:
							nick = await wait_for(get_nick(), 10)
							await client.send_message(from_, "boom boom " + nick)
						except TimeoutError as error:
							logger.warning(str(error))
							await client.answer('error', id_, from_, "no boom :(")
						else:
							await client.answer('result', id_, from_, "boom!")
				
				elif type_ == 'iq.get' and len(elements) == 1 and hasattr(elements[0], 'tag') and elements[0].tag == '{boom}boom-boom-boom' and elements[0].attrib['n'] == '0':
					@client.handle
					async def boom_set(expect, id_=id_, from_=from_):
						sstanza = await expect(lambda _stanza: True)
						stype, sid, sfrom, *selements = await expect(lambda _stype, _sid, _sfrom, *_selements: _stype == 'iq.get' and _sid == id_ and _sfrom == from_)
	
	run(main())

