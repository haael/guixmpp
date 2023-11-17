#!/usr/bin/python3


__all__ = 'asynchandler', 'loop_init', 'loop_run', 'loop_quit'


from asyncio import set_event_loop_policy, get_running_loop, create_task, sleep, wait, FIRST_EXCEPTION, CancelledError
#import gbulb
#import asyncio_glib
from gtkaio import GtkAioEventLoopPolicy
import gi
from gi.repository import Gtk


app_task = None
app_tasks = []
app_future = None


def loop_init():
	set_event_loop_policy(GtkAioEventLoopPolicy())
	#set_event_loop_policy(asyncio_glib.GLibEventLoopPolicy())
	#gbulb.install(gtk=True)


def asynchandler(coro):
	"Takes a coroutine and changes it into normal method that schedules the coroutine and adds the task to the main app task list."
	
	def method(self, *args, **kwargs):
		#print("handler", coro, args, kwargs)
		app_tasks.append(create_task(coro(self, *args, **kwargs)))
		#print(" ", app_task, app_task.done() if app_task else "-")
		if app_task and not app_task.done():
			app_task.cancel()
	
	method.__name__ = coro.__name__
	
	return method


async def loop_run():
	"Run the loop that schedules tasks created by `asynchandler`."
	
	global app_tasks, app_task, app_future
	
	app_tasks = []
	app_future = get_running_loop().create_future()
	
	while True:
		#print("iterate")
		app_task = create_task(wait(app_tasks + [app_future], return_when=FIRST_EXCEPTION))
		
		Gtk.main_iteration_do(False)
		try:
			#print("tasks:", app_tasks)
			await app_task
		except CancelledError:
			#print("cancel")
			pass
		else:
			if app_future.done():
				break
		
		for task in app_tasks[:]:
			if task.done():
				app_tasks.remove(task)
				if task.exception():
					raise task.exception()
	
	assert app_future.done()
	
	return app_future.result()


def loop_quit(result=None):
	"Request to quit the loop. The loop will wait for all tasks to finish. The optional `result` will be returned from `loop_run`."
	
	app_future.set_result(result)
