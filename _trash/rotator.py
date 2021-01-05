#!/usr/bin/python3
#-*- coding:utf-8 -*-


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject as gobject
from gi.repository import GLib as glib
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GdkPixbuf


if __debug__:
	import sys


class Rotator(gtk.Button):
	__gtype_name__ = 'Rotator'
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.angle = 0.3
	
	def set_angle(self, angle):
		self.angle = angle
		self.queue_draw()
	
	def do_draw(self, ctx):
		alloc = self.get_allocation()
		
		x = alloc.x + alloc.width / 12
		y = alloc.y + alloc.height / 12
		w = 2 * alloc.width / 6
		h = 2 * alloc.height / 6
		
		rect = gdk.Rectangle()
		rect.x = x
		rect.y = y
		rect.width = w
		rect.height = h
		self.set_allocation(rect)
		
		ctx.translate(alloc.x, alloc.y)
		
		ctx.translate(alloc.width / 2, alloc.height / 2)
		ctx.rotate(self.angle)
		ctx.translate(-alloc.width / 2, -alloc.height / 2)
		
		gtk.Button.do_draw(self, ctx)

		self.set_allocation(alloc)


if __name__ == '__main__':
	import sys
	import signal
	
	glib.threads_init()
	
	css = gtk.CssProvider()
	css.load_from_path('gfx/style.css')
	gtk.StyleContext().add_provider_for_screen(gdk.Screen.get_default(), css, gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	window = gtk.Window()
	button = gtk.Button()
	label = gtk.Label("aaargh")
	label.set_angle(30)
	button.add(label)
	window.add(button)
	window.show_all()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	window.connect('destroy', lambda widget: mainloop.quit())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()


