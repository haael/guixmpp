#!/usr/bin/python3
#-*- coding: utf-8 -*-

from __future__ import unicode_literals

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib as glib

import cairo
import math

import cairosvg
import cairosvg.surface



class SVGRender:
	def __init__(self, path):
		self.path = path
		self.rendered_svg_surface = None
		self.nodes_under_pointer = None
		
		parent = self
		
		class Surface(cairosvg.surface.Surface):
			def create_recording_surface(self, output, width, height):
				surface = cairo.RecordingSurface(cairo.CONTENT_COLOR, (0, 0, width, height))
				context = cairo.Context(surface)
				context.set_source_rgb(1, 1, 1)
				context.paint()
				return surface
			
			surface_class = create_recording_surface
			
			def finish(self):
				parent.rendered_svg_surface = self.cairo
				parent.nodes_under_pointer = self.hover_nodes
		
		self.Surface = Surface
	
	def render(self, width, height):
		self.Surface.convert(url=self.path, dpi=72, parent_width=width, parent_height=height)
		return self.rendered_svg_surface
	
	def pointer(self, width, height, pointer_x, pointer_y):
		self.Surface.convert(url=self.path, dpi=72, parent_width=width, parent_height=height, mouse=(pointer_x, pointer_y))
		return self.nodes_under_pointer


if __name__ == '__main__':
	import signal
	
	glib.threads_init()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	svgobject = SVGRender('img/status_icons.svg')
	
	window = gtk.Window(gtk.WindowType.TOPLEVEL)
	window.connect('destroy', lambda window: mainloop.quit())
	canvas = gtk.DrawingArea()
	
	rendered_svg_surface = None
	
	def configure_event(canvas, event):
		global rendered_svg_surface
		rect = canvas.get_allocation()
		rendered_svg_surface = svgobject.render(rect.width, rect.height)
	canvas.connect('configure-event', configure_event)
	
	def draw(canvas, context):
		context.set_source_surface(rendered_svg_surface)
		context.paint()
	canvas.connect('draw', draw)
	
	def motion_notify_event(canvas, event):
		rect = canvas.get_allocation()
		nodes_under_pointer = svgobject.pointer(rect.width, rect.height, event.x, event.y)
		print(nodes_under_pointer)
	canvas.connect('motion-notify-event', motion_notify_event)
	
	canvas.add_events(gdk.EventMask.POINTER_MOTION_MASK)
	window.add(canvas)
	window.show_all()
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	







