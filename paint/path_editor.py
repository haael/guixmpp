#!/usr/bin/python3


from logging import getLogger
logger = getLogger(__name__)


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


#from guixmpp import *

from locale import gettext
if not 'Path' in globals(): from aiopath import Path

from math import dist



class PathEditor(Gtk.DrawingArea):
	__gtype_name__ = 'PathEditor'
	
	def __init__(self):
		super().__init__()
		
		self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
		self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
		self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)		
		#self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
		#self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
		#self.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
		
		self.connect('draw', self.draw)
		self.connect('motion-notify-event', self.pointer_event)
		self.connect('button-press-event', self.pointer_event)
		self.connect('button-release-event', self.pointer_event)
		
		#self.__paths = []
		self.__active = {}
		self.__cursor = {}
		self.__last_movement = None
	
	def pointer_event(self, widget, event):
		device = event.get_source_device()
		type_ = device.get_source()
		name = device.get_name()
		self.__last_movement = name
		
		if event.type == Gdk.EventType.MOTION_NOTIFY:
			if name not in self.__cursor:
				self.__cursor[name] = [False, event.x, event.y]
			else:
				self.__cursor[name][1:] = [event.x, event.y]
			
			if self.__cursor[name][0]:
				self.__active[name][1].append((event.x, event.y))
		
		elif event.type == Gdk.EventType.BUTTON_RELEASE:
			#print(name)
			self.__cursor[name] = [False, event.x, event.y]
			if name in self.__active:
				if type_ not in (Gdk.InputSource.TOUCHSCREEN, Gdk.InputSource.ERASER) and len(self.__active[name][1]) > 1:
					#self.__paths.append(self.__active[name][1])
					self.path_ready(self.__active[name][1])
				del self.__active[name]
		
		elif event.type == Gdk.EventType.BUTTON_PRESS:
			self.__cursor[name] = [True, event.x, event.y]
			self.__active[name] = type_, [(event.x, event.y)]
		
		self.queue_draw()
	
	def path_ready(self, path):
		pass
	
	def draw(self, widget, ctx):
		#ctx.set_source_rgba(0, 0.25, 1, 0.25)
		#ctx.paint()
		
		#ctx.set_line_width(2.5)
		#ctx.set_source_rgb(0, 0, 0)
		#
		#for path in self.__paths:
		#	for n, (x, y) in enumerate(path):
		#		if n == 0:
		#			ctx.move_to(x, y)
		#		else:
		#			ctx.line_to(x, y)
		#	
		#	if dist(path[0], path[-1]) < 20:
		#		ctx.close_path()
		#	
		#	ctx.stroke()
		
		for type_, path in self.__active.values():
			if type_ in (Gdk.InputSource.TOUCHSCREEN, Gdk.InputSource.ERASER):
				for n, (x, y) in enumerate(path[-50:]):
					if n == 0:
						ctx.move_to(x, y)
					else:
						ctx.line_to(x, y)
				
				ctx.set_line_width(25)
				ctx.set_source_rgba(1, 0.5, 0.5, 0.75)
			else:
				for n, (x, y) in enumerate(path):
					if n == 0:
						ctx.move_to(x, y)
					else:
						ctx.line_to(x, y)
				
				ctx.set_line_width(2.5)
				ctx.set_source_rgb(0, 0, 0)
			
			ctx.stroke()
		
		try:
			cursor = self.__cursor[self.__last_movement]
		except KeyError:
			pass
		else:
			if not cursor[0]:
				x, y = cursor[1:]
				
				ctx.set_line_width(1)
				ctx.set_source_rgb(0, 0, 1)
				
				ctx.move_to(x - 25, y)
				ctx.rel_line_to(20, 0)
				ctx.stroke()
				
				ctx.move_to(x + 25, y)
				ctx.rel_line_to(-20, 0)
				ctx.stroke()
				
				ctx.move_to(x, y - 25)
				ctx.rel_line_to(0, 20)
				ctx.stroke()
				
				ctx.move_to(x, y + 25)
				ctx.rel_line_to(0, -20)
				ctx.stroke()


if __name__ == '__main__':
	window = Gtk.Window()
	window.add(PathEditor())
	window.show_all()
	window.connect('destroy', lambda *_: Gtk.main_quit())
	Gtk.main()



