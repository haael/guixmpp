#!/usr/bin/python3
#-*- coding: utf-8 -*-


import cairo
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
				parent.background(context)
				return surface
			
			surface_class = create_recording_surface
			
			def finish(self):
				parent.rendered_svg_surface = self.cairo
				parent.nodes_under_pointer = self.hover_nodes
		
		self.Surface = Surface
	
	def background(self, context):
		context.set_source_rgb(1, 1, 1)
		context.paint()
	
	def render(self, width, height):
		self.Surface.convert(url=self.path, dpi=72, parent_width=width, parent_height=height)
		return self.rendered_svg_surface
	
	def pointer(self, width, height, pointer_x, pointer_y):
		self.Surface.convert(url=self.path, dpi=72, parent_width=width, parent_height=height, mouse=(pointer_x, pointer_y))
		return self.nodes_under_pointer


if __name__ == '__main__':
	import signal
	
	import gi	
	gi.require_version('Gtk', '3.0')
	from gi.repository import GObject as gobject
	from gi.repository import Gtk as gtk
	from gi.repository import Gdk as gdk
	from gi.repository import GLib as glib
	
	glib.threads_init()
	
	css = gtk.CssProvider()
	css.load_from_path('gfx/style.css')
	gtk.StyleContext.add_provider_for_screen(gdk.Screen.get_default(), css, gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	window = gtk.Window(gtk.WindowType.TOPLEVEL)
	window.set_name('main_window')
	
	canvas = gtk.DrawingArea()
	
	class SVGRenderBg(SVGRender):
		def background(self, context):
			canvas_allocation = canvas.get_allocation()
			parent = canvas.get_parent()
			parent_allocation = parent.get_allocation()
			style_context = parent.get_style_context()
			gtk.render_background(style_context, context, -canvas_allocation.x, -canvas_allocation.y, parent_allocation.width, parent_allocation.height)
			gtk.render_frame(style_context, context, -canvas_allocation.x, -canvas_allocation.y, parent_allocation.width, parent_allocation.height)
	
	svgobject = SVGRenderBg('gfx/Comparison of several satellite navigation system orbits.svg')
	
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
		if __debug__:
			if nodes_under_pointer:
				print(event.x, event.y, ', '.join([''.join([node.tag, ('#' + node['id'] if ('id' in node) else '')]) for node in nodes_under_pointer]))
	canvas.connect('motion-notify-event', motion_notify_event)
	
	canvas.add_events(gdk.EventMask.POINTER_MOTION_MASK)
	window.add(canvas)
	window.show_all()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	window.connect('destroy', lambda window: mainloop.quit())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	







