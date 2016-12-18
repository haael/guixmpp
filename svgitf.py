#!/usr/bin/python3
#-*- coding: utf-8 -*-

from __future__ import unicode_literals


from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib as glib

import cairo
import math

import cairosvg
import cairosvg.surface


rendered_svg = None
hover_nodes = None


class Surface(cairosvg.surface.Surface):
	def create_recording_surface(self, output, width, height):
		surface = cairo.RecordingSurface(cairo.CONTENT_COLOR, (0, 0, width, height))
		context = cairo.Context(surface)
		context.set_source_rgb(1, 1, 1)
		context.paint()
		return surface
	
	surface_class = create_recording_surface
	
	def finish(self):
		global rendered_svg, hover_nodes
		rendered_svg = self.cairo
		hover_nodes = self.hover_nodes


def resize(widget, event):
	rect = widget.get_allocation()
	Surface.convert(url='img/SVG_logo.svg', dpi=72, parent_width=rect.width, parent_height=rect.height)


def draw(widget, context):
	if rendered_svg:
		context.set_source_surface(rendered_svg)
		context.paint()


def mouse(widget, event):
	print(event.x, event.y)
	rect = widget.get_allocation()
	Surface.convert(url='img/SVG_logo.svg', dpi=72, parent_width=rect.width, parent_height=rect.height, mouse=(event.x, event.y))
	print([node.tag for node in hover_nodes])
	widget.queue_draw()




if __name__ == '__main__':
	import signal
	
	glib.threads_init()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	window = gtk.Window(gtk.WindowType.TOPLEVEL)
	window.connect('destroy', lambda window: mainloop.quit())
	canvas = gtk.DrawingArea()
	canvas.connect('configure-event', lambda canvas, event: resize(canvas, event))
	canvas.connect('draw', lambda canvas, context: draw(canvas, context))
	canvas.connect('motion-notify-event', lambda canvas, event: mouse(canvas, event))
	canvas.add_events(gdk.EventMask.POINTER_MOTION_MASK)
	window.add(canvas)
	window.show_all()
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	







