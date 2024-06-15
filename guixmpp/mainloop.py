#!/usr/bin/python3


__all__ = 'asynchandler', 'loop_init', 'loop_run', 'loop_quit', 'loop_main'


import gi
from gi.repository import Gtk

from asyncio import set_event_loop_policy, get_running_loop, create_task, sleep, wait, FIRST_EXCEPTION, FIRST_COMPLETED, ALL_COMPLETED, CancelledError, Event
import signal


from os import environ
_library = environ.get('GUIXMPP_MAINLOOP', '') # empty or 'gbulb'

if _library == '':
	if __name__ == '__main__':
		from guixmpp.gtkaio import GtkAioEventLoopPolicy
	else:
		from .gtkaio import GtkAioEventLoopPolicy

elif _library == 'gbulb':
	import gbulb

else:
	raise ImportError(f"Unsupported GUIXMPP_MAINLOOP: {_library}")


if _library == '':
	def loop_init():
		set_event_loop_policy(GtkAioEventLoopPolicy())

elif _library == 'gbulb':
	def loop_init():
		gbulb.install(gtk=True)


_loop_tasks = set()
_task_added = Event()
_loop_finished = Event()
_loop_result = None
_loop_error = None










'''
def asynchandler(coro):
	"Takes a coroutine and changes it into normal method that schedules the coroutine and adds the task to the main app task list."
	
	def method(self, *args, **kwargs):
		future = get_running_loop().create_future()
		
		async def guarded_coro(self, *args, **kwargs):
			try:
				value = await coro(self, *args, **kwargs)
			except BaseException as error:
				future.set_exception(error)
				raise
			else:
				future.set_result(value)
				return value
		
		task = create_task(guarded_coro(self, *args, **kwargs), name=coro.__name__)
		app_tasks.append(task)
		task.add_done_callback(app_task.discard)
		if app_task and not app_task.done():
			app_task.cancel()
		return future
	
	method.__name__ = coro.__name__
	
	return method
'''


def asynchandler(coro):
	"Takes a coroutine and changes it into normal method that schedules the coroutine and adds the task to the main app task list."
	
	def method(self, *args, **kwargs):
		task = create_task(coro(self, *args, **kwargs), name=coro.__name__)
		_loop_tasks.add(task)
		task.add_done_callback(_loop_tasks.discard)
		_task_added.set()
		return task
	
	method.__name__ = coro.__name__
	
	return method


'''
async def loop_run():
	"Run the loop that schedules tasks created by `asynchandler`."
	
	global app_tasks, app_task, app_future
	
	get_running_loop().add_signal_handler(signal.SIGTERM, lambda signum: loop_interrupt(SystemExit("SIGTERM")))
	get_running_loop().add_signal_handler(signal.SIGINT, lambda signum: loop_interrupt(KeyboardInterrupt("SIGINT")))
	
	app_tasks = []
	app_future = get_running_loop().create_future()
	
	while True:
		app_task = create_task(wait(app_tasks + [app_future], return_when=FIRST_EXCEPTION))
		
		try:
			await app_task
		except CancelledError:
			pass
		
		for task in app_tasks[:]:
			if task.done():
				app_tasks.remove(task)
				if exc := task.exception():
					raise exc
		
		if app_future.done():
			break
	
	assert app_future.done()
	
	for task in app_tasks:
		if not task.done():
			task.cancel()
	
	return app_future.result()
'''


async def _loop_running():
	await _loop_finished.wait()
	
	if _loop_error is not None:
		raise _loop_error
	else:
		return _loop_result


async def loop_run():
	"Run the loop that schedules tasks created by `asynchandler`."
	
	global _loop_tasks, _task_added
	
	get_running_loop().add_signal_handler(signal.SIGTERM, lambda signum: loop_interrupt(SystemExit("SIGTERM")))
	get_running_loop().add_signal_handler(signal.SIGINT, lambda signum: loop_interrupt(KeyboardInterrupt("SIGINT")))
	
	_loop_tasks = set()
	
	try:
		loop_running_task = create_task(_loop_running(), name='__loop_running')
		while not loop_running_task.done():
			task_added_task = create_task(_task_added.wait(), name='__task_added')
			done, pending = await wait(_loop_tasks | frozenset({loop_running_task, task_added_task}), return_when=FIRST_COMPLETED)
			if not task_added_task.done():
				task_added_task.cancel()
			for task in done:
				if task != loop_running_task:
					await task
		
		assert loop_running_task.done()
		
		errors = []
		
		for task in _loop_tasks:
			task.cancel()
		
		if _loop_tasks:
			done, pending = await wait(_loop_tasks, return_when=ALL_COMPLETED)
			
			for task in done:
				try:
					await task
				except CancelledError:
					pass
				except Exception as exception:
					errors.append(exception)
		
		if errors:
			raise ExceptionGroup("Error cancelling main loop tasks.", errors)
	
	except BaseException as error:
		errors = []
		
		if not loop_running_task.done():
			loop_running_task.cancel()
		
		try:
			await loop_running_task
		except CancelledError:
			pass
		except Exception as exception:
			errors.append(exception)
		
		for task in _loop_tasks:
			task.cancel()
		
		if _loop_tasks:
			done, pending = await wait(_loop_tasks, return_when=ALL_COMPLETED)
			
			for task in done:
				try:
					await task
				except CancelledError:
					pass
				except Exception as exception:
					errors.append(exception)
		
		if errors:
			raise ExceptionGroup("Error cancelling main loop tasks.", errors) from error
		else:
			raise
	
	return await loop_running_task


def loop_quit(result=None):
	"Request to quit the loop. The loop will wait for all tasks to finish. The optional `result` will be returned from `loop_run`."
	
	global _loop_result
	
	_loop_result = result
	_loop_finished.set()


def loop_interrupt(error):
	"Quit the loop immediately. Any running tasks will not be waited for. Exception `error` will be thrown from `loop_run`."
	
	global _loop_error
	
	_loop_error = error
	_loop_finished.set()


async def loop_main(app):
	"Run the specified coroutine in the loop. Quit loop when coroutine ended."
	
	looptask = create_task(loop_run())
	apptask = create_task(app)
	done, pending = await wait([looptask, apptask], return_when=FIRST_COMPLETED)
	
	if looptask in done:
		if not apptask.done():
			apptask.cancel()
	elif apptask in done:
		try:
			result = await apptask
		except BaseException as error:
			loop_interrupt(error)
		else:
			loop_quit(result)
	
	return await looptask

