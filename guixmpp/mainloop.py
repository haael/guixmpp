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
		from guixmpp.gtkaio import GtkAioEventLoopPolicy, GtkAioAppEventLoopPolicy
	else:
		from .gtkaio import GtkAioEventLoopPolicy, GtkAioAppEventLoopPolicy

elif _library == 'gbulb':
	import gbulb

else:
	raise ImportError(f"Unsupported GUIXMPP_MAINLOOP: {_library}")


if _library == '':
	def loop_init(app=None, argv=()):
		global _app
		if app is None:
			set_event_loop_policy(GtkAioEventLoopPolicy())
		else:
			_app = app
			set_event_loop_policy(GtkAioAppEventLoopPolicy(app, argv))

elif _library == 'gbulb':
	def loop_init():
		gbulb.install(gtk=True)


_app = None
_loop_tasks = set()
_task_added = Event()
_loop_finished = Event()
_loop_result = None
_loop_error = None


def _task_done(task):
	_loop_tasks.discard(task)
	if _app is not None:
		_app.release()


def asynchandler(coro):
	"Takes a coroutine and changes it into normal method that schedules the coroutine and adds the task to the main app task list. Returns the task object that can be awaited."
	
	def method(self, *args, **kwargs):
		if _app is not None:
			_app.hold()
		try:
			task = create_task(coro(self, *args, **kwargs), name=coro.__name__)
		except Exception as error:
			raise RuntimeError(f"Error creating task {coro.__name__}") from error
		_loop_tasks.add(task)
		task.add_done_callback(_task_done)
		#task.add_done_callback(_loop_tasks.discard)
		_task_added.set()
		return task
	
	method.__name__ = coro.__name__
	
	return method


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
		task_added_task = None
		while not loop_running_task.done():
			if task_added_task is None:
				task_added_task = create_task(_task_added.wait(), name='__task_added')
			done, pending = await wait(_loop_tasks | frozenset({loop_running_task, task_added_task}), return_when=FIRST_COMPLETED)
			
			if task_added_task.done():
				await task_added_task
				_task_added.clear()
				task_added_task = None
			
			for task in done:
				if task != loop_running_task and task != task_added_task:
					#print(task)
					await task
		
		if task_added_task is not None and not task_added_task.done():
			task_added_task.cancel()
		
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
	"Run the specified coroutine in the loop. Quit loop when coroutine ends."
	
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

