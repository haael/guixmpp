#!/usr/bin/python3

"""
Asyncio path support. This library mimicks the interface of aiopath but uses GLib calls instead of spawning a thread on each async call.
Should be faster than aiopath, but works only when Gtk mainloop is running.
"""


__all__ = 'Path', 'SEEK_SET', 'SEEK_CUR', 'SEEK_END'


import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

from asyncio import Future, gather, to_thread, get_running_loop

from collections import deque
import pathlib
from os import SEEK_SET, SEEK_CUR, SEEK_END
import os.path
import pwd, grp


if __name__ == '__main__':
	from guixmpp.async_helper import AsyncGLibCallHelper as _AsyncIOCall
else:
	from .async_helper import AsyncGLibCallHelper as _AsyncIOCall


class StatResult:
	def __init__(self):
		self.st_uid = 0
		self.st_gid = 0
		
		self.st_atime = 0
		self.st_atime_ns = 0
		self.st_mtime = 0
		self.st_mtime_ns = 0
		self.st_ctime = 0
		self.st_ctime_ns = 0
		self.st_birthtime = 0
		self.st_birthtime_ns = 0
		
		self.st_dev = 0
		self.st_rdev = 0
		self.st_mode = 0
		self.st_ino = 0
		self.st_blocks = 0
		self.st_blksize = 0
		
		self.st_size = 0
		self.st_nlink = 0
		self.st_flags = 0
		self.st_gen = 0
		self.st_fstype = 0
		self.st_rsize = 0
		self.st_creator = 0
		self.st_type = 0
		self.st_file_attributes = 0
		self.st_reparse_tag = 0


class File:
	"Object returned by Path.open() method. Supports interface similar to file-like object, but async."
	
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
	
	__close = _AsyncIOCall((lambda stream, cancellable, on_result: stream.close_async(GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda stream, task: stream.close_finish(task)))
	
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


class Path(pathlib.Path, pathlib.PurePosixPath):
	__slots__ = pathlib.Path.__slots__
	
	@classmethod
	def cwd(cls):
		return cls(GLib.get_current_dir())
	
	@classmethod
	def home(cls):
		return cls(GLib.get_home_dir())
	
	def absolute(self):
		if self.is_absolute():
			return self
		else:
			return self.cwd() / self
	
	async def expanduser(self):
		path = await to_thread(os.path.expanduser, self)
		return self.__class__(path)
	
	async def glob(self, pattern, *, case_sensitive=None):
		return [self.__class__(_path) for _path in await to_thread(pathlib.Path.glob, pathlib.Path(str(self)), pattern)] # TODO add case_sensitive on Python 3.12
	
	async def rglob(self, pattern, *, case_sensitive=None):
		raise NotImplementedError
	
	__query_info = _AsyncIOCall((lambda gfile, attrs, flags, cancellable, on_result: gfile.query_info_async(attrs, flags, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.query_info_finish(task)))
	
	async def __info(self, *attrs, follow_symlinks=True):
		gfile = Gio.File.new_for_path(str(self))
		return await self.__query_info(gfile, ','.join(attrs), Gio.FileQueryInfoFlags.NONE if follow_symlinks else Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS)
	
	async def getmode(self):
		info = await self.__info('unix::mode', 'owner::user', 'owner::group')
		mode = oct(info.get_attribute_uint32('unix::mode'))
		
		u = info.get_attribute_string('owner::user') == await to_thread(lambda: pwd.getpwuid(os.getuid())[0])
		g = info.get_attribute_string('owner::group') in (await to_thread(lambda: [grp.getgrgid(_gid)[0] for _gid in os.getgroups()]))
		
		if u:
			m = int(mode[-3])
		elif g:
			m = int(mode[-2])
		else:
			m = int(mode[-1])
		
		t = []
		if (m >> 2) & 1:
			t.append('r')
		if (m >> 1) & 1:
			t.append('w')
		if (m >> 0) & 1:
			t.append('x')
		
		return ''.join(t)
	
	async def chmod(self, mode, *, follow_symlinks=True):
		raise NotImplementedError
	
	async def exists(self, *, follow_symlinks=True):
		try:
			await self.__info('id::file', follow_symlinks=follow_symlinks)
		except FileNotFoundError:
			return False
		else:
			return True
	
	async def owner(self):
		return (await self.__info('owner::user')).get_attribute_string('owner::user')
	
	async def group(self):
		return (await self.__info('owner::group')).get_attribute_string('owner::group')
	
	async def is_block_device(self) -> bool:
		raise NotImplementedError
		info = await self.__info('standard::type')
		return info.get_attribute_uint32('standard::type') == 999
	
	async def is_char_device(self) -> bool:
		raise NotImplementedError
		info = await self.__info('standard::type')
		return info.get_attribute_uint32('standard::type') == 999
	
	async def is_dir(self) -> bool:
		try:
			info = await self.__info('standard::type')
		except FileNotFoundError:
			return False
		else:
			return info.get_attribute_uint32('standard::type') == 2
	
	async def is_fifo(self) -> bool:
		raise NotImplementedError
		info = await self.__info('standard::type')
		return info.get_attribute_uint32('standard::type') == 999
	
	async def is_file(self) -> bool:
		try:
			info = await self.__info('standard::type')
		except FileNotFoundError:
			return False
		else:
			return info.get_attribute_uint32('standard::type') == 1
	
	async def is_mount(self) -> bool:
		raise NotImplementedError
		info = await self.__info('standard::type')
		return info.get_attribute_uint32('standard::type') == 999
	
	async def is_socket(self) -> bool:
		raise NotImplementedError
		info = await self.__info('standard::type')
		return info.get_attribute_uint32('standard::type') == 999
	
	async def is_symlink(self) -> bool:
		return (await self.__info('standard::is-symlink', follow_symlinks=False)).get_is_symlink()
	
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
	
	async def match(self, path_pattern, *, case_sensitive=None) -> bool:
		raise NotImplementedError
	
	__make_directory = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.make_directory_async(GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.make_directory_finish(task)))
	
	async def mkdir(self, mode=0o777, parents=False, exist_ok=False):
		exists = await self.exists()
		if exists:
			if not exist_ok:
				raise FileExistsError(f"File at the specified destination `{str(self)}` already exists.")
			if not await self.is_dir():
				raise FileExistsError(f"File at the specified destination `{str(self)}` exists and is not a directory.")
			return
		
		if not parents:
			if not await self.parent.exists():
				raise FileNotFoundError(f"Parent directory of `{str(self)}` does not exist.")
			if not await self.parent.is_dir():
				raise FileExistsError(f"Parent of the specified destination `{str(self)}` exists and is not a directory.")
		else:
			path = self.parent
			elements = []
			while not await path.exists():
				elements.append(path)
				path = path.parent
			if not await path.is_dir():
				raise FileExistsError(f"Ancestor `{str(patg)}` of the specified destination `{str(self)}` is not a directory.")
			for path in reversed(elements):
				await path.__make_directory(Gio.File.new_for_path(str(path)))
		
		await self.__make_directory(Gio.File.new_for_path(str(self))) # TODO: mode
	
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
	
	__load_contents = _AsyncIOCall((lambda gfile, *args, cancellable, on_result: gfile.load_contents_async(*args, cancellable, on_result)), (lambda stream, task: stream.load_contents_finish(task)))
	
	async def read_bytes(self):
		while True:
			try:
				return (await self.__load_contents(Gio.File.new_for_path(str(self)))).contents
			except GLib.Error as error:
				if error.code == 0:
					print("ebadf while reading") # FIXME
					continue
				elif error.code == 45:
					print("endpoint protocol not connected") # FIXME
					continue
				raise
	
	__replace_contents = _AsyncIOCall((lambda gfile, data, etag, backup, flags, cancellable, on_result: gfile.replace_contents_async(data, etag, backup, flags, cancellable, on_result)), (lambda stream, task: stream.replace_contents_finish(task)))
	
	async def write_bytes(self, data):
		while True:
			try:
				success = await self.__replace_contents(Gio.File.new_for_path(str(self)), data, None, False, 0)
				if success:
					return len(data)
				else:
					return 0
			except GLib.Error as error:
				if error.code == 0:
					print("ebadf while writing") # FIXME
					continue
				raise
	
	async def read_text(self, encoding='utf-8', errors=None):
		return (await self.read_bytes()).decode(encoding)
	
	async def write_text(self, data, encoding='utf-8', errors=None):
		await self.write_bytes(data.encode(encoding))
	
	async def readlink(self):
		return self.__class__((await self.__info('standard::symlink-target', follow_symlinks=False)).get_symlink_target())
	
	__move = _AsyncIOCall((lambda this, that, flags, cancellable, on_result: this.move_async(that, flags, GLib.PRIORITY_DEFAULT, cancellable, None, None, on_result, None)), (lambda this, task: this.move_finish(task)))
	
	async def rename(self, target):
		"Move file."
		if await self.is_dir():
			return ValueError("Target is a directory.")
		this_gfile = Gio.File.new_for_path(str(self))
		that_gfile = Gio.File.new_for_path(str(target))
		await self.__move(this_gfile, that_gfile)
		return self.__class__(target)
	
	__copy = _AsyncIOCall((lambda this, that, flags, cancellable, on_result: this.copy_async(that, flags, GLib.PRIORITY_DEFAULT, cancellable, None, None, on_result, None)), (lambda this, task: this.copy_finish(task)))
	
	async def replace(self, target):
		"Copy file."
		if await self.is_dir():
			return ValueError("Target is a directory.")
		this_gfile = Gio.File.new_for_path(str(self))
		that_gfile = Gio.File.new_for_path(str(target))
		await self.__copy(this_gfile, that_gfile)
		return self.__class__(target)
	
	__delete = _AsyncIOCall((lambda gfile, cancellable, on_result: gfile.delete_async(GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.delete_finish(task)))
	
	async def rmdir(self):
		"Remove empty directory."
		if not await self.is_dir():
			return ValueError("Target is not a directory.")
		await self.__delete(Gio.File.new_for_path(str(self)))
	
	async def unlink(self, missing_ok=False):
		"Remove file (non-directory)."
		if await self.is_dir():
			return ValueError("Target is a directory.")
		await self.__delete(Gio.File.new_for_path(str(self)))
	
	async def resolve(self, strict=False):
		path = await to_thread(pathlib.Path.resolve, pathlib.Path(self), strict=strict)
		return self.__class__(path)
	
	async def samefile(self, other_path):
		ia, ib = await gather(self.__info('id::file'), other_path.__info('id::file'))
		return ia.get_attribute_string('id::file') == ib.get_attribute_string('id::file')
	
	async def stat(self, *, follow_symlinks=True):
		info = await self.__info('time::*', 'unix::*')
		#for attr in info.list_attributes():
		#	print(attr, info.get_attribute_data(attr))
		
		#result = os.stat_result([0] * 10) #object.__new__(os.stat_result)
		result = StatResult()
		
		result.st_uid = info.get_attribute_uint32('unix::uid')
		result.st_gid = info.get_attribute_uint32('unix::gid')
		
		result.st_atime = info.get_attribute_uint64('time::access')
		result.st_atime_ns = info.get_attribute_uint64('time::access') * 1000000 + info.get_attribute_uint32('time::access-nsec')
		result.st_mtime = info.get_attribute_uint64('time::modified')
		result.st_mtime_ns = info.get_attribute_uint64('time::modified') * 1000000 + info.get_attribute_uint32('time::modified-nsec')
		result.st_ctime = info.get_attribute_uint64('time::changed')
		result.st_ctime_ns = info.get_attribute_uint64('time::changed') * 1000000 + info.get_attribute_uint32('time::changed-nsec')
		result.st_birthtime = info.get_attribute_uint64('time::created')
		result.st_birthtime_ns = info.get_attribute_uint64('time::created') * 1000000 + info.get_attribute_uint32('time::created-nsec')
		
		result.st_dev = info.get_attribute_uint32('unix::device')
		result.st_rdev = info.get_attribute_uint32('unix::rdev')
		result.st_mode = info.get_attribute_uint32('unix::mode')
		result.st_ino = info.get_attribute_uint64('unix::inode')
		result.st_blocks = info.get_attribute_uint64('unix::blocks')
		result.st_blksize = info.get_attribute_uint32('unix::block-size')
		
		'''
		result.st_size
		st_nlink
		st_flags
		st_gen
		st_fstype
		st_rsize
		st_creator
		st_type
		st_file_attributes
		st_reparse_tag
		'''
		
		return result
	
	async def lstat(self):
		raise NotImplementedError
	
	__make_symbolic_link = _AsyncIOCall((lambda gfile, target, cancellable, on_result: gfile.make_symbolic_link_async(target, GLib.PRIORITY_DEFAULT, cancellable, on_result)), (lambda gfile, task: gfile.make_symbolic_link_finish(task)))
	
	async def symlink_to(self, target, target_is_directory=False):
		await self.__make_symbolic_link(Gio.File.new_for_path(str(self)), str(target))
	
	async def hardlink_to(self, target):
		raise NotImplementedError
	
	async def touch(self, mode=0o666, exist_ok=True):
		f = self.open('a' if exist_ok else 'x') # TODO: mode
		await f.open()
		await f.close()


if __name__ == '__main__':
	from guixmpp.gtkaio import GtkAioEventLoopPolicy
	from asyncio import set_event_loop_policy, run
	
	set_event_loop_policy(GtkAioEventLoopPolicy())
	
	async def test():
		cwd = Path.cwd()
		print(repr(cwd))
		
		fst = cwd / '../fstabbing/guixmpp'
		assert await fst.is_symlink()
		assert await (await (fst.parent / (await fst.readlink())).resolve()).samefile(cwd / 'guixmpp')
		assert await (cwd / '../fstabbing/guixmpp').samefile(cwd / 'guixmpp')
		assert not await (cwd / '../fstabbing/guixmpp').samefile(cwd / 'examples')
		
		print(await Path('/').owner(), await Path('/').group())
		
		async with (cwd / 'ttt1.txt').open('wb') as fd:
			await fd.write(b"teeest me")
		
		print("modes:", await (cwd / 'ttt1.txt').owner(), await (cwd / 'ttt1.txt').group(), await (cwd / 'ttt1.txt').getmode())
		
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
		
		await gather((cwd / 'ttt1.txt').unlink(), (cwd / 'ttt2.txt').unlink())
	
	run(test())


