#!/usr/bin/python3

"""
Asyncio path support. This library mimicks the interface of aiopath but uses GLib calls instead of spawning a thread on each async call.
Should be faster than aiopath, but works only when Gtk mainloop is running.
"""


__all__ = 'PurePath', 'Path'


import gi
gi.require_version('GLib', '2.0')
from gi.repository import Gio, GLib

from asyncio import Future, get_running_loop

from collections import deque
import pathlib
from os import SEEK_SET, SEEK_CUR, SEEK_END


class _AsyncIOCall:
	def __init__(self, init=None, finish=None):
		self._init = init
		self._finish = finish
	
	def init(self, *args, cancellable, on_result):
		self._init(*args, cancellable=cancellable, on_result=on_result)
	
	def finish(self, obj, task):
		return self._finish(obj, task)
	
	def __call__(self, *args):
		future = get_running_loop().create_future()
		cancellable = Gio.Cancellable()
		
		def on_done(future):
			if future.cancelled():
				cancellable.cancel() # cancel Gio operation
		
		future.add_done_callback(on_done)
		
		def on_result(obj, task):
			try:
				result = self.finish(obj, task)
			except GLib.Error as error:
				future.set_exception(error)
			else:
				future.set_result(result)
		
		self.init(*args, cancellable=cancellable, on_result=on_result)
		
		return future


class File:
	def __init__(self, path, mode, buffering, encoding, errors, newline):
		self.gfile = Gio.File.new_for_path(str(path))
		self.mode = mode
		self.buffering = buffering
		self.encoding = encoding
		self.errors = errors
		self.newline = newline
		self.__eof = False
		self.__read_buffer = bytearray()
	
	def __del__(self):
		if hasattr(self, 'stream'):
			raise ValueError(f"Lost reference to open file: {self.gfile}") # will be logged
	
	__open_readwrite = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.open_readwrite_async(GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.open_readwrite_finish(task))) # r+
	__open_readonly = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.read_async(GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.read_finish(task))) # r
	__create_readwrite = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.create_readwrite_async(GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.create_readwrite_finish(task))) # x+
	__create_writeonly = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.create_async(GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.create_finish(task))) # x
	__replace_readwrite = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.replace_readwrite_async(GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.replace_readwrite_finish(task))) # w+
	__replace_writeonly = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.replace_async(None, False, 0, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.replace_finish(task))) # w
	__append_writeonly = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.append_to_async(0, cancellable, on_result)), (lambda gfile, task: gfile.append_to_finish(task))) # a
	
	__read = _AsyncIOCall((lambda stream, num, cancellable, on_result: stream.read_bytes_async(num, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda stream, task: stream.read_bytes_finish(task)))
	__write = _AsyncIOCall((lambda stream, bytes_, cancellable, on_result: stream.write_async(bytes_, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda stream, task: stream.write_finish(task)))
	__write_all = _AsyncIOCall((lambda stream, bytes_, cancellable, on_result: stream.write_all_async(bytes_, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda stream, task: stream.write_all_finish(task)))
	
	__close = _AsyncIOCall((lambda stream, *args, cancellable, on_result: stream.close_async(*args, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda stream, task: stream.close_finish(task)))
	
	async def open(self):
		if 'r' in self.mode and '+' not in self.mode:
			self.stream = self.read_stream = await self.__open_readonly(self.gfile)
			self.write_stream = None
		elif 'r' in self.mode and '+' in self.mode:
			self.stream = await self.__open_readwrite(self.gfile)
			self.read_stream = self.stream.get_input_stream()
			self.write_stream = self.stream.get_output_stream()
		
		elif 'w' in self.mode and '+' not in self.mode:
			self.read_stream = None
			self.stream = self.write_stream = await self.__replace_writeonly(self.gfile)
		elif 'w' in self.mode and '+' in self.mode:
			self.stream = await self.__replace_readwrite(self.gfile)
			self.read_stream = self.stream.get_input_stream()
			self.write_stream = self.stream.get_output_stream()
		
		elif 'x' in self.mode and '+' not in self.mode:
			self.read_stream = None
			self.stream = self.write_stream = await self.__create_writeonly(self.gfile)
		elif 'x' in self.mode and '+' in self.mode:
			self.stream = await self.__create_readwrite(self.gfile)
			self.read_stream = self.stream.get_input_stream()
			self.write_stream = self.stream.get_output_stream()
		
		elif 'a' in self.mode:
			self.read_stream = None
			self.stream = self.write_stream = await self.__append_writeonly(self.gfile)
		
		else:
			raise ValueError("Invalid file mode.")
	
	async def close(self):
		await self.__close(self.stream)
		del self.stream, self.read_stream, self.write_stream
		self.__read_buffer.clear()
	
	async def __aenter__(self):
		await self.open()
		return self
	
	async def __aexit__(self, *args):
		await self.close()
	
	async def __aiter__(self):
		while True:
			line = await self.readline()
			if not line:
				break
			yield line
	
	async def is_eof(self):
		return self.__eof
	
	async def read(self, n):
		if not self.read_stream:
			raise IOError("Stream is not readable.")
		
		if not self.__eof and len(self.__read_buffer) < n:
			chunk = (await self.__read(self.read_stream, n - len(self.__read_buffer))).get_data()
			if not chunk:
				self.__eof = True
			self.__read_buffer += chunk
		
		result = bytes(self.__read_buffer[:n])
		del self.__read_buffer[:n]
		
		if self.encoding:
			return result.decode(self.encoding)
		else:
			return result
	
	async def readline(self):
		while not self.__eof and self.newline not in self.__read_buffer:
			chunk = (await self.__read(self.read_stream, 4096)).get_data()
			if not chunk:
				self.__eof = True
				break
			self.__read_buffer += chunk
		
		if self.newline in self.__read_buffer:
			p = self.__read_buffer.index(self.newline) + 1
			result = bytes(self.__read_buffer[:p])
			del self.__read_buffer[:p]
		else:
			result = bytes(self.__read_buffer)
			self.__read_buffer.clear()
		
		if self.encoding:
			return result.decode(self.encoding)
		else:
			return result
	
	async def read_all(self):
		while not self.__eof:
			chunk = (await self.__read(self.read_stream, 4096)).get_data()
			if not chunk:
				self.__eof = True
			self.__read_buffer += chunk
		
		result = bytes(self.__read_buffer)
		self.__read_buffer.clear()
		
		if self.encoding:
			return result.decode(self.encoding)
		else:
			return result
	
	async def write(self, data):
		if not self.write_stream:
			raise IOError("Stream is not writable.")
		
		if self.encoding:
			data = data.encode(self.encoding)
		
		return await self.__write(self.write_stream, data)
	
	async def write_all(self, data):
		if not self.write_stream:
			raise IOError("Stream is not writable.")
		
		if self.encoding:
			data = data.encode(self.encoding)
		
		return await self.__write_all(self.write_stream, data)
	
	async def seek(self, offset, whence=SEEK_SET):
		if whence == SEEK_SET:
			w = GLib.SeekType.SET
		elif whence == SEEK_CUR:
			w = GLib.SeekType.CUR
		elif whence == SEEK_END:
			w = GLib.SeekType.END
		else:
			raise ValueError("Allowed values for whence: SEEK_SET, SEEK_CUR, SEEK_END.")
		self.stream.seek(offset, w)
	
	async def tell(self):
		return self.stream.tell()


class PurePath(pathlib.PurePosixPath):
	__slots__ = pathlib.PurePosixPath.__slots__
	
	def __rtruediv__(self, key):
		return Path(super().__rtruediv__(key))
	
	def __truediv__(self, key):
		return Path(super().__truediv__(key))
	
	@property
	def parent(self):
		return Path(super().parent)
	
	@property
	def parents(self):
		return tuple(Path(path) for path in super().parents)
	
	def joinpath(self, *pathsegments):
		return Path(super().joinpath(*pathsegments))
	
	def relative_to(self, other, /, *_deprecated, walk_up=False):
		return Path(super().relative_to(other, *_deprecated, walk_up=walk_up))
	
	def with_name(self, name):
		return Path(super().with_name(name))
	
	def with_suffix(self, suffix):
		return Path(super().with_suffix(suffix))


class Path(pathlib.Path, PurePath):
	__slots__ = pathlib.Path.__slots__
	
	@classmethod
	def cwd(cls):
		return cls(GLib.get_current_dir())
	
	@classmethod
	def home(cls):
		return cls(GLib.get_home_dir())
	
	async def absolute(self):
		raise NotImplementedError
		path = await get_running_loop().run_in_executor(None, pathlib.Path.absolute, self)
		return Path(path)
	
	async def chmod(self, mode, *, follow_symlinks=True):
		raise NotImplementedError
	
	async def exists(self, *, follow_symlinks=True):
		raise NotImplementedError
	
	async def expanduser(self):
		path = await get_running_loop().run_in_executor(None, pathlib.Path.expanduser, self)
		return Path(path)
	
	async def glob(self, pattern, *, case_sensitive=None):
		raise NotImplementedError
		for path in await get_running_loop().run_in_executor(None, pathlib.Path.glob, self, pattern, case_sensitive=case_sensitive):
			yield Path(path)
	
	async def rglob(self, pattern, *, case_sensitive=None):
		raise NotImplementedError
		for path in await get_running_loop().run_in_executor(None, pathlib.Path.rglob, self, pattern, case_sensitive=case_sensitive):
			yield Path(path)
	
	async def group(self):
		raise NotImplementedError
	
	async def hardlink_to(self, target):
		raise NotImplementedError
	
	async def is_block_device(self) -> bool:
		raise NotImplementedError
	
	async def is_char_device(self) -> bool:
		raise NotImplementedError
	
	async def is_dir(self) -> bool:
		raise NotImplementedError
	
	async def is_fifo(self) -> bool:
		raise NotImplementedError
	
	async def is_file(self) -> bool:
		raise NotImplementedError
	
	async def is_mount(self) -> bool:
		raise NotImplementedError
	
	async def is_socket(self) -> bool:
		raise NotImplementedError
	
	async def is_symlink(self) -> bool:
		raise NotImplementedError
	
	__enumerate_children = _AsyncIOCall((lambda gfile, x, y, cancellable, on_result: gfile.enumerate_children_async(x, y, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda obj, task: obj.enumerate_children_finish(task)))
	__next_files = _AsyncIOCall((lambda enumerator, n, cancellable, on_result: enumerator.next_files_async(n, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda enumerator, task: enumerator.next_files_finish(task)))
	
	async def iterdir(self):
		enumerator = await self.__enumerate_children(Gio.File.new_for_path(str(self)), Gio.FILE_ATTRIBUTE_STANDARD_NAME, 0)
		something = True
		while something:
			file_list = await self.__next_files(enumerator, 4) # read 4 items at once
			something = False
			for f in file_list:
				something = True
				yield self / f.get_name()
	
	async def lchmod(self, mode):
		raise NotImplementedError
	
	async def lstat(self):
		raise NotImplementedError
	
	async def match(self, path_pattern, *, case_sensitive=None) -> bool:
		raise NotImplementedError
	
	async def mkdir(self, mode=0o777, parents=False, exist_ok=False):
		raise NotImplementedError
	
	def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=b"\n"):
		if 't' in mode and 'b' in mode:
			raise ValueError("Text and binary modes are exclusive.")
		
		if 'b' in mode and encoding:
			raise ValueError("Can not set encoding in binary mode.")
		
		if 'b' not in mode and not encoding:
			encoding = 'utf-8'
		
		if encoding and not isinstance(newline, bytes):
			newline = newline.encode(encoding)
		
		return File(self, mode, buffering, encoding, errors, newline)
	
	async def owner(self):
		raise NotImplementedError
	
	__load_contents = _AsyncIOCall((lambda gfile, *args, cancellable, on_result: gfile.load_contents_async(*args, cancellable, on_result)), (lambda stream, task: stream.load_contents_finish(task)))
	
	async def read_bytes(self):		
		return (await self.__load_contents(Gio.File.new_for_path(str(self)))).contents
	
	__replace_contents = _AsyncIOCall((lambda gfile, *args, cancellable, on_result: gfile.replace_contents_async(*args, cancellable, on_result)), (lambda stream, task: stream.replace_contents_finish(task)))
	
	async def write_bytes(self, data):
		success = await self.__replace_contents(Gio.File.new_for_path(str(self)), data, len(data), None, False, 0)
		if success:
			return len(data)
		else:
			return 0
	
	async def read_text(self, encoding='utf-8', errors=None):
		return (await self.read_bytes()).decode(encoding)
	
	async def write_text(self, data, encoding='utf-8', errors=None):
		await self.write_bytes(data.encode(encoding))
	
	async def readlink(self):
		raise NotImplementedError
		return Path(path)
	
	async def rename(self, target):
		raise NotImplementedError
		return Path(path)
	
	async def replace(self, target):
		raise NotImplementedError
		return Path(path)
	
	async def resolve(self, strict=False):
		raise NotImplementedError
		return Path(path)
	
	async def rmdir(self):
		raise NotImplementedError
	
	async def samefile(self, other_path):
		raise NotImplementedError
	
	async def stat(self, *, follow_symlinks=True):
		raise NotImplementedError
	
	async def symlink_to(self, target, target_is_directory=False):
		raise NotImplementedError
	
	async def touch(self, mode=0o666, exist_ok=True):
		raise NotImplementedError
	
	async def unlink(self, missing_ok=False):
		raise NotImplementedError


if __name__ == '__main__':
	from guixmpp.gtkaio import GtkAioEventLoopPolicy
	from asyncio import set_event_loop_policy, run
	
	set_event_loop_policy(GtkAioEventLoopPolicy())
	
	async def test():
		cwd = await Path.cwd()
		print(repr(cwd))
		
		async with (cwd / 'ttt1.txt').open('wb') as fd:
			await fd.write(b"teeest me")

		async with (cwd / 'ttt2.txt').open('w') as fd:
			await fd.write("teeest me tooo")
		
		async for f in cwd.iterdir():
			print("", repr(f))
			if f.suffix == '.txt':
				print(" read bytes")
				print(await f.read_bytes())
				print(" read text")
				print(await f.read_text())
				print(" read parts")
				async with f.open() as fd:
					print(await fd.read(5))
					print(await fd.tell())
					await fd.seek(4)
					print(await fd.read_all())
				print(" read lines")
				async with f.open() as fd:
					async for l in fd:
						print(l)
	
	run(test())


