#!/usr/bin/python3


__all__ = 'AsyncGLibCallHelper',


import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

from asyncio import get_running_loop


class AsyncGLibCallHelper:
	def __init__(self, init=None, finish=None):
		self._init = init
		self._finish = finish
	
	def init(self, *args, cancellable, on_result):
		self._init(*args, cancellable=cancellable, on_result=on_result)
	
	def finish(self, obj, task):
		if obj is not None:
			return self._finish(obj, task)
		else:
			return self._finish(task)
	
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
				if error.code == 1: # file not found
					future.set_exception(FileNotFoundError(str(error)))
				elif error.code == 19: # cancelled
					pass
				else:
					# TODO: raise proper exception classes instead of GLib.Error
					future.set_exception(error)
			except BaseException as error:
				future.set_exception(error)
			else:
				future.set_result(result)
		
		self.init(*args, cancellable=cancellable, on_result=on_result)
		
		return future

