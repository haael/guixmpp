#!/usr/bin/python3


"""
Simple XMPP client for asyncio.

This is a complete rewrite based on: <https://github.com/stan-janssen/tinyxmpp>.
"""

__author__ = 'https://github.com/haael'
__credits__ = 'https://github.com/stan-janssen', 'https://github.com/staseek'
__license__ = 'Apache 2.0'
__all__ = 'XMPPClient', 'XMPPError', 'ProtocolError', 'StreamError', 'AuthenticationError', 'QueryError'


from logging import getLogger
logger = getLogger(__name__)

from asyncio import open_connection, wait_for, Lock, CancelledError, Queue, Event, Condition, get_running_loop, gather, create_task, wait, FIRST_EXCEPTION, FIRST_COMPLETED, ALL_COMPLETED, sleep
from ssl import create_default_context
from lxml.etree import fromstring, tostring, XMLPullParser
from scramp import ScramClient, ScramMechanism
from base64 import b64encode, b64decode
from secrets import token_urlsafe
from collections import Counter, deque
from contextvars import ContextVar


class XMPPError(Exception):
	pass


class ProtocolError(XMPPError):
	"Unexpected tag in XMPP stream."


class StreamError(XMPPError):
	"XML parse error in XMPP stream."


class AuthenticationError(XMPPError):
	"Error in authentication."


class QueryError(XMPPError):
	"Error related to IQ request."


class XMPPClient:
	namespace = {
		'stream': 'http://etherx.jabber.org/streams',
		'client': 'jabber:client',
		'iq-register': 'http://jabber.org/features/iq-register',
		'xmpp-tls': 'urn:ietf:params:xml:ns:xmpp-tls',
		'xmpp-sasl': 'urn:ietf:params:xml:ns:xmpp-sasl',
		'xmpp-streams': 'urn:ietf:params:xml:ns:xmpp-streams',
		'xmpp-stanzas': 'urn:ietf:params:xml:ns:xmpp-stanzas',
		'xmpp-bind': 'urn:ietf:params:xml:ns:xmpp-bind',
		'xep-0077': 'jabber:iq:register'
	}
	
	def __init__(self, jid, password=None, config=None):
		self.jid = jid
		self.password = password
		
		self.established = False
		self.encrypted = False
		self.authenticated = False
		self.state_condition = Condition()
		
		self.read_lock = Lock()
		self.write_lock = Lock()
		
		self.task_queue = ContextVar('task_queue')
		self.inside_task = ContextVar('inside_task')
		self.inside_task.set(False)
		self.expectations = Queue()
		self.n_tasks = 0
		self.end_of_stream = Event()
		
		self.__tasks = set()
		self.__task_added = Event()
		
		self.recv_stanza_counter = 0
		self.sent_stanza_counter = 0
		
		self.config = {
			'host': None,
			'port': None,
			'legacy_ssl': False,
			'ssl_timeout': 10,
			'end_timeout': 4,
			'encryption_required': True
		}
		
		if config:
			self.config.update(config)
	
	def ssl_context(self):
		return create_default_context()
	
	def random_token(self):
		return token_urlsafe(6)
	
	async def get_password(self, jid, anonymous_ok):
		"None - no login, empty string - anonymous login, normal string - SASL login"
		return self.password
	
	async def connect(self):
		"Open network connection to XMPP server."
		
		host = self.config['host']
		if not host: host = self.jid.split('@')[1].split('/')[0] # TODO: SRV record
		
		legacy_ssl = self.config['legacy_ssl']
		
		port = self.config['port']
		if not port: port = 5223 if legacy_ssl else 5222
		
		timeout = self.config['ssl_timeout']
		
		logger.info(f"Connecting to XMPP server {host}:{port}, legacy_ssl={legacy_ssl}.")
		
		if not timeout:
			self.reader, self.writer = await open_connection(host, port, ssl=legacy_ssl)
		else:
			self.reader, self.writer = await wait_for(open_connection(host, port, ssl=legacy_ssl), timeout)
		
		self.encrypted = bool(legacy_ssl)
	
	async def disconnect(self):
		"Close network connection to XMPP server."
		
		logger.info("Disconnecting from XMPP server.")
		self.writer.close()
		await self.writer.wait_closed()
		del self.reader, self.writer
	
	async def begin_stream(self, bare_jid=None, server=None):
		"Send the opening tag in XMPP stream."
		
		async with self.state_condition:
			logger.info("Begin XMPP stream.")
			
			async with (self.read_lock, self.write_lock):
				self.parser = XMLPullParser(events=['start', 'end'])
				
				if not bare_jid: bare_jid = self.jid.split('/')[0]
				if not server: server = self.jid.split('@')[1].split('/')[0]
				
				data = f'<?xml version="1.0"?><stream:stream from="{bare_jid}" to="{server}" version="1.0" xmlns="{self.namespace["client"]}" xmlns:stream="{self.namespace["stream"]}">'.encode('utf-8')
				self.writer.write(data)
				await self.writer.drain()
				
				stream_tag = False
				while not stream_tag:
					data = await self.reader.readuntil(b'>')
					self.parser.feed(data)
					for event, element in self.parser.read_events(): # TODO: raise StreamError on parsing error
						if event == 'start' and element.tag == f'{{{self.namespace["stream"]}}}stream':
							stream_tag = True
						else:
							logger.error(f"Received unexpected tag: {element.tag}")
							raise ProtocolError("Expected <stream> opening tag.")
				
				self.end_of_stream.clear()
				self.sent_stanza_counter = 0
				self.recv_stanza_counter = 0
			
			self.established = True
			self.authenticated = False
			self.state_condition.notify_all()
	
	async def end_stream(self):
		"Send the ending tag in XMPP stream, wait for close."
		
		async with self.state_condition:
			logger.info("End XMPP stream.")

			async with (self.read_lock, self.write_lock):
				self.writer.write(b'</stream:stream>')
				await self.writer.drain()
				
				if self.established:
					end_timeout = self.config['end_timeout']
					try:
						self.read_lock.release()
						self.state_condition.release()
						
						stanza = ''
						while stanza != None:
							logger.info("Waiting for end tag... ")
							stanza = await self.recv_stanza() # TODO: wait_for
							if stanza != None:
								try:
									logger.warning(f"Garbage stanza received: {tostring(stanza).decode('utf-8')}")
								except TypeError:
									logger.warning(f"Non-stanza garbage received: {repr(stanza)}")
					except TimeoutError:
						logger.debug("Timeout waiting for end tag.")
					finally:
						await self.state_condition.acquire()
						await self.read_lock.acquire()
			
			self.established = False
			self.authenticated = False
			del self.parser
			self.state_condition.notify_all()
	
	async def send_stanza(self, stanza):
		"Send raw stanza on the stream."
		
		async with self.state_condition:
			await self.state_condition.wait_for(lambda: self.established)
		
		async with self.write_lock:
			rawdata = tostring(stanza)
			self.writer.write(rawdata)
			logger.debug(f"sending stanza: {tostring(stanza).decode('utf-8')}")
			await self.writer.drain()
			self.sent_stanza_counter += 1
	
	async def recv_stanza(self):
		"Receive raw stanza from the stream. Will return None when stream ends."
		
		if self.inside_task.get():
			return await self.expect('self::*')
		
		async with self.state_condition:
			await self.state_condition.wait_for(lambda: self.established)
		
		async with self.read_lock:
			while True:
				rawdata = await self.reader.readuntil(b'>')
				self.parser.feed(rawdata)
				for event, element in self.parser.read_events():
					if event != 'end': continue
					
					if element.tag == f'{{{self.namespace["stream"]}}}stream' and element.getparent() == None:
						logger.debug(f"Received stream end tag.")
						self.end_of_stream.set()
						return None
					elif element.getparent().tag == f'{{{self.namespace["stream"]}}}stream' and element.getparent().getparent() == None:
						#logger.debug(f"received stanza: {tostring(element).decode('utf-8')}.")
						self.recv_stanza_counter += 1
						return element
	
	async def __aenter__(self):
		await self.connect()
		await self.begin_stream()
		return self
	
	async def __aexit__(self, exctype, exception, traceback):
		errors = []
		if self.__tasks:
			logger.warning(f"Some of tasks still running. {self__tasks}")
			self.cancel()
			logger.debug("Waiting for remaining tasks to finish.")
			done, pending = await wait(self.__tasks, return_when=ALL_COMPLETED)
			assert not pending
			for task in done:
				try:
					await task
				except Exception as exception:
					errors.append(exception)
				except CancelledError:
					pass
		
		await self.end_stream()
		await self.disconnect()
		
		logger.info("XMPP client exit.")
		
		if errors:
			if exception:
				raise ExceptionGroup("Error cancelling one of XMPP tasks.", errors) from exception
			else:
				raise ExceptionGroup("Error cancelling one of XMPP tasks.", errors)
	
	def create_task(self, coro, name=None):
		logger.info(f"Creating new task{ ' (' + name + ')' if name is not None else ''}.")
		task = create_task(coro, name=name)
		self.__tasks.add(task)
		task.add_done_callback(self.__tasks.discard)
		self.__task_added.set()
		return task
	
	def cancel(self):
		logger.info("Cancelling all tasks.")
		for task in self.__tasks:
			if not task.done():
				task.cancel()
	
	async def process(self):
		expectations = []
		async def gather_expectations():
			logger.debug(f"gather expectations {self.n_tasks} - {len(expectations)} = {self.n_tasks - len(expectations)}")
			for n in range(self.n_tasks - len(expectations)):
				expectation = await self.expectations.get()
				expectations.append(expectation)
		
		stanza = None
		try:
			logger.info("XMPPClient main loop begin.")
			
			while self.n_tasks:
				#logger.debug(f"process {self.n_tasks}")
				gather_expectations_task = self.create_task(gather_expectations(), name='__gather_expectations') # TODO: wait_for
				recv_stanza_task = self.create_task(self.recv_stanza(), name='__recv_stanza')
				
				del stanza
				while self.n_tasks and not (gather_expectations_task.done() and recv_stanza_task.done()):
					task_added = create_task(self.__task_added.wait(), name='__check_if_task_added')
					self.__task_added.clear()
					done, pending = await wait(self.__tasks | frozenset({task_added}), return_when=FIRST_COMPLETED)
					if not task_added.done():
						task_added.cancel()
					for task in done:
						result = await task
						if task == recv_stanza_task:
							stanza = result
				
				if not self.n_tasks:
					break
				
				if stanza is not None:
					for xpath, namespaces, queue in expectations[:]:
						if queue is None:
							expectations.remove((xpath, namespaces, queue))
							continue
						els = stanza.xpath(xpath, namespaces=(namespaces if (namespaces is not None) else self.namespace))
						if not els:
							#logger.debug(f"No match `{xpath}` with element: {tostring(stanza)}.")
							continue
						expectations.remove((xpath, namespaces, queue))
						logger.debug(f"Match found for xpath `{xpath}`.")
						await queue.put(els[0])
				else:
					for xpath, namespaces, queue in expectations[:]:
						expectations.remove((xpath, namespaces, queue))
						if queue is None: continue
						await queue.put(None)
					break
			
			logger.info("XMPPClient main loop ended.")
			
			if self.__tasks:
				if not gather_expectations_task.done(): gather_expectations_task.cancel()
				if not recv_stanza_task.done(): recv_stanza_task.cancel()
				done, pending = await wait(self.__tasks, return_when=ALL_COMPLETED) # TODO: timeout
				assert not pending
				errors = []
				for task in done:
					try:
						await task
					except Exception as exception:
						errors.append(exception)
					except CancelledError:
						pass
				if errors:
					raise ExceptionGroup("Error at exit from one of XMPP tasks.", errors)
		
		except BaseException as error:
			if not self.__tasks:
				raise
			logger.warning(f"Error in XMPPClient mainloop: {type(error)} {str(error)}.")
			self.cancel()
			done, pending = await wait(self.__tasks, return_when=ALL_COMPLETED)
			assert not pending
			errors = []
			for task in done:
				try:
					await task
				except Exception as exception:
					errors.append(exception)
				except CancelledError:
					pass
			if errors:
				raise ExceptionGroup("Error cancelling one of XMPP tasks.", errors) from error
			else:
				raise
		
	def task(self, coro):
		"Start a task that is able to receive stanzas in parallel with other tassk."
		
		async def ncoro():
			try:
				self.inside_task.set(True)
				queue = Queue()
				self.task_queue.set(queue)
				await coro(self)
			finally:
				self.n_tasks -= 1
		
		self.n_tasks += 1
		return self.create_task(ncoro(), name=coro.__name__)
	
	async def expect(self, xpath, namespaces=None):
		"Wait for stanza matching the provided xpath. Will return None when stream ends."
		
		#logger.debug(f"expect {xpath}")
		
		if not self.inside_task.get():
			while True:
				stanza = await self.recv_stanza()
				if stanza is None:
					return
				els = stanza.xpath(xpath, namespaces=(namespaces if (namespaces is not None) else self.namespace))
				if els:
					return els[0]
			raise RuntimeError("I shouldn't be here.")
		
		if self.end_of_stream.is_set():
			raise CancelledError("End of stream.")
		queue = self.task_queue.get()
		await self.expectations.put((xpath, namespaces, queue))
		return await queue.get()
	
	async def starttls(self):
		"Upgrade connection to TLS."
		
		logger.info("Initiating STARTTLS procedure.")
		
		await self.send_stanza(fromstring(f'<starttls xmlns="{self.namespace["xmpp-tls"]}"/>'))
		stanza = await self.recv_stanza()
		if stanza.tag != f'{{{self.namespace["xmpp-tls"]}}}proceed':
			raise ProtocolError(f"Expected starttls proceed stanza, got {stanza.tag}")
		
		async with self.state_condition:
			self.established = False
			self.state_condition.notify_all()
		
		logger.info("Upgrading transport to TLS.")
		
		host = self.config['host']
		if not host: host = self.jid.split('@')[1].split('/')[0]
		
		ssl = self.ssl_context()
		
		timeout = self.config['ssl_timeout']
		
		await self.writer.start_tls(ssl, server_hostname=host, ssl_handshake_timeout=timeout)
		
		async with self.state_condition:
			self.encrypted = True
			self.state_condition.notify_all()
		
		await self.begin_stream()
	
	async def authenticate(self, feature):
		"Authenticate to the server using SASL. This method should be used in response to <mechanisms/> feature."
		
		if not self.encrypted:
			raise ProtocolError("By config, encryption is mandatory for authentication.")
		
		mechanisms = [_mechanism.text for _mechanism in feature if _mechanism.tag == f'{{{self.namespace["xmpp-sasl"]}}}mechanism']
		
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
			await self.send_stanza(fromstring(f'<auth xmlns="{self.namespace["xmpp-sasl"]}" mechanism="{scram.mechanism_name}">{b64encode(message.encode("utf-8")).decode("utf-8")}</auth>'))
			
			stanza = await self.recv_stanza()
			if stanza.tag == f'{{{self.namespace["xmpp-sasl"]}}}failure':
				try:
					status = "Unauthorized: " + [_child.text for _child in stanza if _child.tag == f'{{{self.namespace["xmpp-sasl"]}}}text'][0]
				except (IndexError, TypeError):
					status = "Unauthorized."
				raise AuthenticationError(status)
			if stanza.tag != f'{{{self.namespace["xmpp-sasl"]}}}challenge':
				raise ProtocolError("Expected SASL challenge.")
			message = b64decode(stanza.text).decode("utf-8")
			logger.debug(f"Server challenge: {message}")
			scram.set_server_first(message)
			
			message = scram.get_client_final()
			logger.debug(f"Client response: {message}")
			await self.send_stanza(fromstring(f'<response xmlns="{self.namespace["xmpp-sasl"]}">{b64encode(message.encode("utf-8")).decode("utf-8")}</response>'))
			
			stanza = await self.recv_stanza()
			if stanza.tag == f'{{{self.namespace["xmpp-sasl"]}}}failure':
				try:
					status = "Unauthorized: " + [_child.text for _child in stanza if _child.tag == f'{{{self.namespace["xmpp-sasl"]}}}text'][0]
				except (IndexError, TypeError):
					status = "Unauthorized."
				raise AuthenticationError(status)
			if stanza.tag != f'{{{self.namespace["xmpp-sasl"]}}}success':
				raise ProtocolError("Expected SASL success.")
			message = b64decode(stanza.text).decode("utf-8")
			logger.debug(f"Server result: {message}")
			scram.set_server_final(message)
		
		else:
			raise NotImplementedError("Anonymous login not implemented yet.")
		
		logger.info("Authorized.")
		await self.begin_stream()
		self.authenticated = True
		return True
	
	async def bind(self, resource=None):
		if resource is None:
			resource = self.jid.split('/')[1]
		
		stanza = await self.iq_set(None, fromstring(f'<bind xmlns="{self.namespace["xmpp-bind"]}"><resource>{resource}</resource></bind>'))
		if stanza.tag != f'{{{self.namespace["xmpp-bind"]}}}bind':
			raise ProtocolError(f"Unable to bind resource: unexpected response tag: {stanza.tag}")
		
		try:
			jid = [_child.text for _child in stanza if _child.tag == f'{{{self.namespace["xmpp-bind"]}}}jid'][0]
		except IndexError:
			raise ProtocolError("Unable to bind resource: JID not found in server response.")
		
		logger.info(f"Bound resource: {jid}")
		
		self.jid = jid
		return jid
	
	'''
	async def on_iq(self, stanza):
		logger.debug(f"Received IQ stanza id:{stanza.attrib.get('id', None)}.")
		
		id_ = stanza.attrib.get('id', None)
		if id_ in self.iq_requests:
			future = self.iq_requests[id_]
		else:
			future = None
			#raise ProtocolError(f"Unexpected response for IQ that wasn't requested: {id_}.")
		
		try:
			method = stanza.attrib['type']
			if method in ('result', 'error'):
				if future:
					future.set_result(stanza)
				else:
					logger.warning(f"Unexpected response for IQ that wasn't requested: {id_}: {stanza}.")
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
		except Exception as error:
			if future:
				future.set_exception(error)
			else:
				raise
		
	async def on_query(self, method, id_, from_, *body):
		if self.config['ping'] and len(body) == 1 and hasattr(body[0], 'tag') and body[0].tag == '{urn:xmpp:ping}ping':
			logger.info(f"Ping from <{from_}>.")
			await self.answer('result', id_, from_)
		else:
			return await self.on_other_query(method, id_, from_, *body)
	
	
	async def message(self, to, svg_body=None, html_body=None, text_body=None):
		message = fromstring(f'<message to="{to}"/>')
		
		if svg_body is not None:
			if html_body is None:
				raise ValueError
			
			svg_body.tail = "\n"
			message.append(svg_body)
		
		if html_body:
			if not text_body:
				raise ValueError
			html_body.tail = "\n" + text_body
			message.append(html_body)
		
		if svg_body is None and html_body is None:
			if not text_body:
				raise ValueError
			
			message.text = text_body
		
		await self.send_stanza(message)
	
	async def presence(self, to=None, type_=None, show=None, status=None, priority=None):
		presence = fromstring('<presence/>')
		if to:
			presence.attrib['to'] = to
		if type_:
			presence.attrib['type'] = type_
		if show is not None:
			presence.append(fromstring(f'<show>{show}</show>'))
		if status is not None:
			presence.append(fromstring(f'<status>{status}</status>'))
		if priority is not None:
			presence.append(fromstring(f'<priority>{priority}</priority>'))
		await self.send_stanza(presence)
	'''
	
	async def iq_get(self, to, body, timeout=10):
		return await self.query('get', to, body, timeout=timeout)
	
	async def iq_set(self, to, body, timeout=10):
		return await self.query('set', to, body, timeout=timeout)
	
	async def iq_result(self, id_, to, body):
		return await self.answer('result', id_, to, None, body)
	
	async def iq_error(self, id_, to, error, body):
		return await self.answer('error', id_, to, error, body)
	
	async def query(self, method, to, body, timeout=10):
		"Do GET or SET (IQ) request."
		
		if method not in ('get', 'set'):
			raise ValueError
		
		if not (isinstance(to, str) or to == None):
			raise ValueError # TODO: validate jid
		
		id_ = self.random_token()
		if to:
			iq = fromstring(f'<iq id="{id_}" type="{method}" to="{to}"/>')
		else:
			iq = fromstring(f'<iq id="{id_}" type="{method}"/>')
		
		iq.append(body)
		
		await self.send_stanza(iq)
		if timeout is None:
			result = await self.expect(f'self::client:iq[@id="{id_}" and (@type="result" or @type="error")]')
		else:
			result = await wait_for(self.expect(f'self::client:iq[@id="{id_}" and (@type="result" or @type="error")]'), timeout)
		
		if result.attrib['type'] == 'result':
			if len(result) == 0:
				return None
			elif len(result) == 1:
				return result[0]
			else:
				raise ProtocolError("Expected result with 0 or 1 children.")
		elif result.attrib['type'] == 'error':
			errors = [_error for _error in result if _error.tag == f'{{{self.namespace["client"]}}}error']
			if len(errors) != 1:
				raise ProtocolError("Expected exactly 1 error child.")
			
			logger.error("Query error.")
			raise QueryError(errors[0])
		else:
			raise RuntimeError
	
	async def answer(self, method, id_, to, error, body):
		if method not in ('result', 'error'):
			raise ValueError(f"Expected 'result' or 'error'; got '{method}'.")
		
		if not id_:
			raise ValueError(f"Id is required on an IQ stanza.")
		
		iq = fromstring(f'<iq id="{id_}" type="{method}" to="{to}"/>')
		
		if body is not None:
			iq.append(body)
		
		if error is not None:
			iq.append(error)
		
		await self.send_stanza(iq)
	
	async def login(self, timeout=10):
		"Login sequence."
		
		while True:
			if timeout is None:
				features = await self.expect('self::stream:features')
			else:
				features = await wait_for(self.expect('self::stream:features'), timeout)
			
			if features is None: # end of stream
				logger.warning("Stream ended prematurely.")
			elif any(_child.tag == f'{{{self.namespace["xmpp-tls"]}}}starttls' for _child in features):
				if self.encrypted:
					raise ProtocolError("STARTTLS is possible only on unencrypted stream.")
				await self.starttls()
			elif any(_child.tag == f'{{{self.namespace["xmpp-sasl"]}}}mechanisms' for _child in features):
				feature = [_child for _child in features if _child.tag == f'{{{self.namespace["xmpp-sasl"]}}}mechanisms'][0]
				result = await self.authenticate(feature)
				if not result:
					logger.info("Initialization sequence ended without login attempt.")
					break
			elif any(_child.tag == f'{{{self.namespace["xmpp-bind"]}}}bind' for _child in features):
				if not self.authenticated:
					raise ProtocolError("Binding available only after authentication.")
				jid = await self.bind()
				logger.debug(f"Bound to jid: {jid}.")
				logger.info("Initialization sequence complete.")
				break
			else:
				logging.error("No required features found.")
				raise ProtocolError("Initialization sequence failed.")



if __name__ == '__main__':
	from logging import DEBUG, StreamHandler
	logger.setLevel(DEBUG)
	logger.addHandler(StreamHandler())
	
	from asyncio import run
	
	s = fromstring('<stream:stream xmlns:stream="http://etherx.jabber.org/streams"/>')
	f = fromstring('<stream:features xmlns:stream="http://etherx.jabber.org/streams" xmlns="jabber:client"><qqqq/><starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"><required/></starttls></stream:features>')
	s.append(f)
	
	assert not f.xpath('/stream:features/xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert not f.xpath('./stream:features/xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert not f.xpath('stream:features/xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert f.xpath('//stream:features/xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert f.xpath('self::stream:features/xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert f.xpath('../stream:features/xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert f.xpath('*', namespaces=XMPPClient.namespace)
	assert f.xpath('.', namespaces=XMPPClient.namespace)
	assert not f.xpath('/', namespaces=XMPPClient.namespace)
	assert f.xpath('/*', namespaces=XMPPClient.namespace)
	
	assert not f.xpath('/xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert f.xpath('./xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert f.xpath('xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	assert f.xpath('//xmpp-tls:starttls', namespaces=XMPPClient.namespace)
	
	assert not f.xpath('/xmpp-tls:required', namespaces=XMPPClient.namespace)
	assert not f.xpath('./xmpp-tls:required', namespaces=XMPPClient.namespace)
	assert not f.xpath('xmpp-tls:required', namespaces=XMPPClient.namespace)
	assert f.xpath('//xmpp-tls:required', namespaces=XMPPClient.namespace)
	
	assert not f.xpath('/stream:features', namespaces=XMPPClient.namespace)
	assert not f.xpath('./stream:features', namespaces=XMPPClient.namespace)
	assert not f.xpath('stream:features', namespaces=XMPPClient.namespace)
	assert f.xpath('//stream:features', namespaces=XMPPClient.namespace)
	
	async def main():
		async with XMPPClient('haael@jabber.cz/discovery') as client:
			if False:
				@client.task
				async def starttls(client):
					print("starttls task")
					await client.expect('self::stream:features/xmpp-tls:starttls')
					await client.starttls()
					print("starttls end")
				
				@client.task
				async def auth(client):
					print("auth task")
					mechanisms = [_mechanism.text for _mechanism in await client.expect('self::stream:features/xmpp-sasl:mechanisms') if _mechanism.tag == f'{{{client.namespace["xmpp-sasl"]}}}mechanism']
					await client.authenticate(mechanisms)
				
				@client.task
				async def bind_res(client):
					print("bind task")
					await client.expect('self::stream:features/xmpp-bind:bind')
					print("got bind")
			
			else:
				@client.task
				async def register(client, timeout=10):
					while True:
						if timeout is None:
							features = await client.expect('self::stream:features')
						else:
							features = await wait_for(client.expect('self::stream:features'), timeout)
						
						if features is None: # end of stream
							logger.warning("Stream ended prematurely.")
							return
						elif any(_child.tag == f'{{{client.namespace["xmpp-tls"]}}}starttls' for _child in features):
							await client.starttls()
						elif any(_child.tag == f'{{{client.namespace["iq-register"]}}}register' for _child in features):
							break
						else:
							raise ProtocolError("Initialization sequence failed.")
					
					server_jid = client.jid.split('@')[1].split('/')[0]
					r = await client.iq_get(server_jid, fromstring(f'<query xmlns="{client.namespace["xep-0077"]}"/>'))
					print(tostring(r, pretty_print=True).decode('utf-8'))
				
				#@client.task
				async def answer_ping(client):
					self.namespace['xep-0199'] = 'urn:xmpp:ping'
					try:
						while (stanza := await client.expect(f'self::client:iq[@type="get"]/xep-0199:ping')) is not None:
							try:
								id_ = stanza.attrib['id']
								type_ = stanza.attrib['type']
							except KeyError: # error: id or type missing
								continue
							
							if type_ == 'get':
								peer = stanza.attrib.get('from', None)
								logger.info(f"Ping from {peer}.")
								await client.iq_result(id_, peer)
							elif type_ == 'set':
								await client.iq_error(id_, peer, fromstring('<error/>')) # TODO
					finally:
						del self.namespace['xep-0199']
				
				#@client.task
				async def invalid_iq_errors(client):
					"Send errors in response to invalid <iq/>s."
					
					while (stanza := await client.expect(f'self::client:iq')) is not None:
						id_ = stanza.attrib['id']
						peer = stanza.attrib.get('from', None)
						
						type_ = stanza.attrib.get('type', None)
						if type_ in ('result', 'error'):
							pass
						elif type_ in ('get', 'set'):
							errors = []
							for child in stanza:
								if child.nsmap not in self.namespace.values():
									errors.append(fromstring('<error/>')) # TODO
							if errors:
								await client.iq_error(id_, peer, *errors)
						else:
							await client.iq_error(id_, peer, fromstring('<error/>')) # TODO
			
			await client.process()
			
	
	run(main())

