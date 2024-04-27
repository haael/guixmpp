#!/usr/bin/python3

"""
Asyncio path support. This library mimicks the interface of aiopath but uses GLib calls instead of spawning a thread on each async call.
Should be faster than aiopath, but works only with gtkaio.
"""

raise NotImplementedError("Module not ready yet")


import gi
gi.require_version('GLib', '2.0')
from gi.repository import Gio, GLib

from asyncio import Future, get_running_loop

import pathlib


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
	async def cwd(cls):
		return cls(GLib.get_current_dir())
	
	@classmethod
	async def home(cls):
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
		raise NotImplementedError
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
	
	async def iterdir(self):
		path = Gio.File.new_for_path(str(self))
		
		future1 = get_running_loop().create_future()
		cancellable1 = Gio.Cancellable()
		
		def on_done1(future):
			if future.cancelled():
				cancellable1.cancel()
		
		future1.add_done_callback(on_done1)
		
		def on_result1(stream, task):
			try:
				enumerator = stream.enumerate_children_finish(task)
			except GLib.Error as error:
				future1.set_exception(error)
			else:
				future1.set_result(enumerator)
		
		path.enumerate_children_async(Gio.FILE_ATTRIBUTE_STANDARD_NAME, 0, GLib.PRIORITY_DEFAULT, cancellable1, on_result1)
		
		enumerator = await future1
		
		something = True
		while something:
			future2 = get_running_loop().create_future()
			cancellable2 = Gio.Cancellable()
			
			def on_done2(future):
				if future.cancelled():
					cancellable2.cancel()
			
			future2.add_done_callback(on_done2)
			
			def on_result2(enumerator, task):
				try:
					file_list = enumerator.next_files_finish(task)
				except GLib.Error as error:
					future2.set_exception(error)
				else:
					future2.set_result(file_list)
			
			enumerator.next_files_async(4, GLib.PRIORITY_DEFAULT, cancellable2, on_result2)
			
			file_list = await future2
			
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
	
	#def open(self, mode=FileMode, buffering=-1, encoding=None, errors=None, newline=None):
	#	raise NotImplementedError
	
	async def owner(self):
		raise NotImplementedError
	
	async def read_bytes(self):
		path = Gio.File.new_for_path(str(self))
		future = get_running_loop().create_future()
		cancellable = Gio.Cancellable()
		
		def on_done(future):
			if future.cancelled():
				cancellable.cancel()
		
		future.add_done_callback(on_done)
		
		def on_result(stream, task):
			try:
				result = stream.load_contents_finish(task)
			except GLib.Error as error:
				future.set_exception(error)
			else:
				future.set_result(result.contents)
		
		path.load_contents_async(cancellable, on_result)
		
		return await future
	
	async def write_bytes(self, data):
		path = Gio.File.new_for_path(str(self))
		future = get_running_loop().create_future()
		cancellable = Gio.Cancellable()
		
		def on_done(future):
			if future.cancelled():
				cancellable.cancel()
		
		future.add_done_callback(on_done)
		
		def on_result(stream, task):
			try:
				success = stream.replace_contents_finish(task)
			except GLib.Error as error:
				future.set_exception(error)
			else:
				if success:
					future.set_result(len(data))
				else:
					future.set_result(0)
		
		path.replace_contents_async(data, len(data), None, False, 0, cancellable, on_result)
		
		return await future
	
	async def read_text(self, encoding=None, errors=None):
		raise NotImplementedError
	
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
	
	async def write_text(self, data, encoding=None, errors=None, newline=None):
		raise NotImplementedError


if __name__ == '__main__':
	from guixmpp.gtkaio import GtkAioEventLoopPolicy
	from asyncio import set_event_loop_policy, run
	
	set_event_loop_policy(GtkAioEventLoopPolicy())
	
	async def test():
		cwd = await Path.cwd()
		print(repr(cwd))
		async for f in cwd.iterdir():
			print("", repr(f))
			if f.suffix == '.txt':
				print(await f.read_bytes())
	
	run(test())


