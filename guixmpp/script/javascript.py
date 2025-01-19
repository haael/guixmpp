#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'JSFormat', 'JSDocument'


#if __name__ == '__main__':
#	import sys
#	del sys.path[0]


from sys import stdin
from asyncio import create_subprocess_exec, StreamReader, StreamWriter, StreamReaderProtocol, get_running_loop, wait_for, sleep, create_task, Lock
from asyncio.streams import FlowControlMixin
from asyncio.exceptions import IncompleteReadError, CancelledError
from subprocess import PIPE
from os import pipe, set_blocking
from pickle import loads, dumps

from gi.repository import Gio
from guixmpp.gtkaio import SubprocessTransport


end_of_transmission = bytes([0x04])
file_separator = bytes([0x1c])
group_separator = bytes([0x1d])
record_separator = bytes([0x1e])
unit_separator = bytes([0x1f])


class JSDocument:
	def __init__(self, content):
		self.content = content


def locked(old_meth):
	async def new_meth(self, *args, **kwargs):
		async with self._JSFormat__lock:
			return old_meth(self, *args, **kwargs)
	return new_meth


class JSFormat:
	def __init__(self, *args, javascript_engine='./guixmpp/engine.py', **kwargs):
		self.javascript_engine = javascript_engine
		self.__script_vars = {}
		self.__lock = Lock()
	
	@locked
	async def on_open_document(self, view, document):
		read_fd_in, write_fd_in = pipe()
		read_fd_out, write_fd_out = pipe()
		set_blocking(write_fd_in, False)
		set_blocking(read_fd_out, False)
		
		self.__engine = await create_subprocess_exec(self.javascript_engine, str(read_fd_in), str(write_fd_out), stdin=PIPE, pass_fds=(read_fd_in, write_fd_out))
		loop = get_running_loop()
		
		self.__reader = reader = StreamReader(loop=loop)
		r_transport, r_protocol = await loop.connect_read_pipe(lambda: SubprocessTransport.ReaderProtocol(read_fd_out, self.__engine._transport), Gio.UnixInputStream.new(read_fd_out, True))
		reader.set_transport(r_transport)
		r_protocol._stream_reader = reader
		
		w_transport, w_protocol = await loop.connect_write_pipe(lambda: SubprocessTransport.WriterProtocol(write_fd_in, self.__engine._transport), Gio.UnixOutputStream.new(write_fd_in, True))
		self.__writer = writer = StreamWriter(w_transport, w_protocol, None, loop)
		w_protocol._stream_writer = writer
		
		await r_transport.start()
		await w_transport.start()
		
		self.__events = create_task(self.__serve_events())
	
	@locked
	async def on_close_document(self, view, document):
		await self.__engine.stdin.drain()
		self.__engine.stdin.write(end_of_transmission)
		self.__engine.stdin.write(file_separator)
		self.__engine.stdin.write_eof()
		self.__engine.stdin.close()
		
		self.__writer.close()
		
		self.__events.cancel()
		try:
			await self.__events
		except CancelledError:
			pass
		
		try:
			await wait_for(self.__engine.wait(), 1)
		except TimeoutError:
			print("warning: I had to kill engine")
			# TODO: warning
			self.__engine.kill()
			await self.__engine.wait()
		
		del self.__reader, self.__writer, self.__engine, self.__events
	
	def create_document(self, data:bytes, mime:str):
		if mime == 'application/javascript':
			document = JSDocument(data.decode('utf-8'))
			return document
		else:
			return NotImplemented
	
	def is_js_document(self, document):
		return isinstance(document, JSDocument)
	
	def scan_document_links(self, document):
		if self.is_js_document(document):
			return []
		else:
			return NotImplemented
	
	async def get_script_var(self, key):
		if key == 'window.title':
			return "Title"
		
		try:
			return self.__script_vars[key]
		except KeyError:
			return None
	
	async def set_script_var(self, key, value):
		self.__script_vars[key] = value
	
	async def __serve_events(self):
		while hasattr(self, '_JSFormat__reader') and hasattr(self, '_JSFormat__writer'):
			try:
				msg = await self.__reader.readuntil(group_separator)
			except IncompleteReadError:
				break
			else:
				records = msg[:-1].split(record_separator)
				if not msg:
					break
			
			if records[0] == 'get'.encode('utf-8'):
				assert len(records) == 2
				key = records[1].decode('utf-8')
				value = await self.get_script_var(key)
				data = dumps(value)
				await self.__writer.drain()
				self.__writer.write(data)
				self.__writer.write(group_separator)
			elif records[0] == 'set'.encode('utf-8'):
				assert len(records) == 3
				key = records[1].decode('utf-8')
				data = records[2]
				value = loads(data)
				await self.set_script_var(key, value)
			else:
				pass # TODO: warning
	
	@locked
	async def run_script(self, document):
		if not self.is_js_document(document):
			return NotImplemented
		
		if not document.content:
			return
		
		await self.__engine.stdin.drain()
		self.__engine.stdin.write('application/javascript'.encode('utf-8'))
		self.__engine.stdin.write(group_separator)
		self.__engine.stdin.write(document.content.encode('utf-8'))
		self.__engine.stdin.write(file_separator)


if __debug__ and __name__ == '__main__':
	from asyncio import run, set_event_loop_policy
	from guixmpp.gtkaio import GtkAioEventLoopPolicy
	set_event_loop_policy(GtkAioEventLoopPolicy())
	
	#from pathlib import Path
	
	print("javascript")
	
	model = JSFormat()
	
	async def test_1():
		a = model.create_document(b'''
			
			var a = 1;
			
			function hello()
			{
				console.log("hello void");
				a += 1;
			}
			
			hello();
			
		''', 'application/javascript')
		assert model.is_js_document(a)
		
		b = model.create_document(b'''
			
			var b;
			
			function get_title()
			{
				console.log("hello");
				var t = window.title;
				console.log("Received:", t);
				hello();
				b = a + 1;
				window.result = b;
			}
			get_title();
			
		''', 'application/javascript')
		assert model.is_js_document(b)
		
		await model.on_open_document(None, True)
		await model.run_script(a)
		await model.run_script(b)
		await sleep(3) # let the scripts finish
		result = await model.get_script_var('window.result')
		assert result == 4, str(result)
		await model.on_close_document(None, True)
	
	run(test_1())
	
	quit()
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		for jsfile in example.iterdir():
			if jsfile.suffix != '.js': continue
			document = model.create_document(jsfile.read_bytes(), 'application/javascript')
			assert model.is_js_document(document)

