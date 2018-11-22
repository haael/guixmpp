#!/usr/bin/python3
#-*- coding: utf-8 -*-


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from domevents import *
import cairo

import cairosvg.surface
import cairosvg.parser

from enum import Enum
from math import hypot


class SVGRender(cairosvg.surface.Surface):
	def create_recording_surface(self, output, width, height):
		surface = cairo.RecordingSurface(cairo.CONTENT_COLOR, (0, 0, width, height))
		self.rendered_svg_surface = surface
		context = cairo.Context(surface)
		self.background(context)
		return surface

	surface_class = create_recording_surface

	def finish(self):
		if self.rendered_svg_surface is not self.cairo:
			self.rendered_svg_surface = self.cairo

		try:
			self.nodes_under_pointer = self.hover_nodes
		except AttributeError:
			self.nodes_under_pointer = []

	def background(self, context):
		context.set_source_rgb(1, 1, 1)
		context.paint()

	@classmethod
	def render(cls, tree, width, height):
		instance = cls(tree=tree, output=None, dpi=72, parent_width=width, parent_height=height)
		instance.finish()
		return instance.rendered_svg_surface

	@classmethod
	def pointer(cls, tree, width, height, pointer_x, pointer_y):
		instance = cls(tree=tree, output=None, dpi=72, parent_width=width, parent_height=height, mouse=(pointer_x, pointer_y))
		instance.finish()
		return instance.nodes_under_pointer, instance.rendered_svg_surface


class SVGWidget(gtk.DrawingArea):
	__gsignals__ = { \
		'clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
	}

	EMPTY_SVG = b'''<?xml version="1.0" encoding="UTF-8"?>
		<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 1 1" width="1px" height="1px">
		</svg>
	'''

	CLICK_TIME = float("inf")
	CLICK_RANGE = 5

	class Keys(Enum):
		SHIFT = 1
		ALT = 2
		CTRL = 4
		META = 8

	def __init__(self):
		super().__init__()

		class SVGRenderBg(SVGRender):
			canvas = self

			def background(self, context):
				canvas = self.canvas
				canvas_allocation = canvas.get_allocation()
				parent = canvas.get_parent()
				parent_allocation = parent.get_allocation()
				style_context = parent.get_style_context()
				gtk.render_background(style_context, context, -canvas_allocation.x, -canvas_allocation.y, parent_allocation.width, parent_allocation.height)
				gtk.render_frame(style_context, context, -canvas_allocation.x, -canvas_allocation.y, parent_allocation.width, parent_allocation.height)

		self.SVGRenderBg = SVGRenderBg

		if __debug__:
			self.emitted_dom_events = list()

		self.document = cairosvg.parser.Tree(bytestring=self.EMPTY_SVG)

		self.rendered_svg_surface = None
		self.nodes_under_pointer = []
		self.previous_nodes_under_pointer = []
		self.current_click_count = 0
		self.last_mousedown = None
		self.connect('configure-event', self.handle_configure_event)
		self.connect('draw', self.handle_draw)
		self.connect('motion-notify-event', self.handle_motion_notify_event)
		self.connect('button-press-event', self.handle_button_press_event)
		self.connect('button-release-event', self.handle_button_release_event)
		self.connect('clicked', self.handle_clicked)

		if __debug__: print("{:10} | {:10} | {:10}".format("Type", "Target", "relatedTarget"));
		self.add_events(gdk.EventMask.POINTER_MOTION_MASK)
		self.add_events(gdk.EventMask.BUTTON_RELEASE_MASK)
		self.add_events(gdk.EventMask.BUTTON_PRESS_MASK)

	def load_url(self, url):
		self.document = cairosvg.parser.Tree(url=url)
		if self.get_realized():
			rect = self.get_allocation()
			self.rendered_svg_surface = self.SVGRenderBg.render(self.document, rect.width, rect.height)
		self.queue_draw()

	@classmethod
	def check_click_hysteresis(cls, press_event, event):
		if hypot(press_event.x - event.x, press_event.y - event.y) < cls.CLICK_RANGE \
		   and (event.get_time() - press_event.get_time()) < cls.CLICK_TIME:
			return True
		return False

	@classmethod
	def gen_node_parents(cls, node):
		if node.parent:
			yield from cls.gen_node_parents(node.parent)
		yield node

	@classmethod
	def get_keys(cls, event):
		return {cls.Keys.SHIFT: bool(event.state & gdk.ModifierType.SHIFT_MASK),\
				cls.Keys.CTRL: bool(event.state & gdk.ModifierType.CONTROL_MASK),\
				cls.Keys.ALT: bool(event.state & (gdk.ModifierType.MOD1_MASK | gdk.ModifierType.MOD5_MASK)),\
				cls.Keys.META: bool(event.state & (gdk.ModifierType.META_MASK | gdk.ModifierType.SUPER_MASK | gdk.ModifierType.MOD4_MASK))}

	@staticmethod
	def get_pressed_mouse_buttons_mask(event):
		active_buttons = 0
		if event.state & gdk.ModifierType.BUTTON1_MASK:
			active_buttons |= 1
		if event.state & gdk.ModifierType.BUTTON3_MASK:
			active_buttons |= 2
		if event.state & gdk.ModifierType.BUTTON2_MASK:
			active_buttons |= 4
		return active_buttons

	@staticmethod
	def get_pressed_mouse_button(event):
		active_button = 0
		if event.button == gdk.BUTTON_PRIMARY:
			active_button = 0
		elif event.button == gdk.BUTTON_SECONDARY:
			active_button = 2
		elif event.button == gdk.BUTTON_MIDDLE:
			active_button = 1
		return active_button

	def update_nodes_under_pointer(self, event):
		self.previous_nodes_under_pointer = self.nodes_under_pointer
		rect = self.get_allocation()
		self.nodes_under_pointer, self.rendered_svg_surface = self.SVGRenderBg.pointer(self.document, rect.width, rect.height, event.x, event.y)

	def handle_configure_event(self, drawingarea, event):
		rect = self.get_allocation()
		self.rendered_svg_surface = self.SVGRenderBg.render(self.document, rect.width, rect.height)

	def handle_draw(self, drawingarea, context):
		if self.rendered_svg_surface:
			context.set_source_surface(self.rendered_svg_surface)
		else:
			context.set_source_rgba(1, 1, 1)
		context.paint()

	def handle_motion_notify_event(self, drawingarea, event):
		if self.last_mousedown and not self.check_click_hysteresis(self.last_mousedown, event):
			self.last_mousedown = None
		self.update_nodes_under_pointer(event)
		if self.previous_nodes_under_pointer != self.nodes_under_pointer:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			keys = self.get_keys(event)
			#~ if __debug__: print(len(self.nodes_under_pointer));

			if self.previous_nodes_under_pointer:
				if self.nodes_under_pointer:
					related = self.nodes_under_pointer[-1]
				else:
					related = None
				ms_ev = MouseEvent("mouseout", target=self.previous_nodes_under_pointer[-1], \
									clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
									shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
									altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
									buttons=mouse_buttons, relatedTarget=related)
				if __debug__: print("{:10} | {:10} | {:10}".format(ms_ev.type_, ms_ev.target.get('fill'), ms_ev.relatedTarget.get('fill') if ms_ev.relatedTarget else "None"));
				self.emit_dom_event("motion_notify_event", ms_ev)
				if related:
					for nodes_target in self.previous_nodes_under_pointer:
						if nodes_target not in self.nodes_under_pointer:
							ms_ev = MouseEvent("mouseleave", target=nodes_target, \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons, relatedTarget=related)
							if __debug__: print("{:10} | {:10} | {:10}".format(ms_ev.type_, ms_ev.target.get('fill'), ms_ev.relatedTarget.get('fill') if ms_ev.relatedTarget else "None"));
							self.emit_dom_event("motion_notify_event", ms_ev)
				else:
					for nodes_target in self.previous_nodes_under_pointer:
						ms_ev = MouseEvent("mouseleave", target=nodes_target, \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons, relatedTarget=related)
						if __debug__: print("{:10} | {:10} | {:10}".format(ms_ev.type_, ms_ev.target.get('fill'), ms_ev.relatedTarget.get('fill') if ms_ev.relatedTarget else "None"));
						self.emit_dom_event("motion_notify_event", ms_ev)

			if self.nodes_under_pointer:
				if self.previous_nodes_under_pointer:
					related = self.previous_nodes_under_pointer[-1]
				else:
					related = None
				ms_ev = MouseEvent("mouseover", target=self.nodes_under_pointer[-1], \
									clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
									shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
									altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
									buttons=mouse_buttons, relatedTarget=related)
				if __debug__: print("{:10} | {:10} | {:10}".format(ms_ev.type_, ms_ev.target.get('fill'), ms_ev.relatedTarget.get('fill') if ms_ev.relatedTarget else "None"));
				self.emit_dom_event("motion_notify_event", ms_ev)
				if related:
					for nodes_target in reversed(self.nodes_under_pointer):
						if nodes_target not in self.previous_nodes_under_pointer:
							ms_ev = MouseEvent("mouseenter", target=nodes_target, \
											clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
											shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
											altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
											buttons=mouse_buttons, relatedTarget=related)
							if __debug__: print("{:10} | {:10} | {:10}".format(ms_ev.type_, ms_ev.target.get('fill'), ms_ev.relatedTarget.get('fill') if ms_ev.relatedTarget else "None"));
							self.emit_dom_event("motion_notify_event", ms_ev)
				else:
					for nodes_target in reversed(self.nodes_under_pointer):
						ms_ev = MouseEvent("mouseenter", target=nodes_target, \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons, relatedTarget=related)

						if __debug__: print("{:10} | {:10} | {:10}".format(ms_ev.type_, ms_ev.target.get('fill'), ms_ev.relatedTarget.get('fill') if ms_ev.relatedTarget else "None"));
						self.emit_dom_event("motion_notify_event", ms_ev)

		#~ elif self.previous_nodes_under_pointer:
		if self.nodes_under_pointer:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			keys = self.get_keys(event)
			ms_ev = MouseEvent("mousemove", target=self.nodes_under_pointer[-1], \
							clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
							shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
							altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
							buttons=mouse_buttons)
			if __debug__: print("{:10} | {:10} | {:10}".format(ms_ev.type_, ms_ev.target.get('fill'), ms_ev.relatedTarget.get('fill') if ms_ev.relatedTarget else "None"));
			self.emit_dom_event("motion_notify_event", ms_ev)
		#canvas.queue_draw()

		if __debug__: self.check_dom_events("motion_notify_event")

	def handle_button_press_event(self, drawingarea, event):
		if self.nodes_under_pointer:
			#~ if __debug__: print("\n".join(str(i) for i in self.gen_node_parents(self.nodes_under_pointer[-1])))
			self.current_click_count += 1
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			mouse_button = self.get_pressed_mouse_button(event)
			keys = self.get_keys(event)
			ms_ev = MouseEvent(	"mousedown", target=self.nodes_under_pointer[-1], \
								detail=self.current_click_count, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("handle_button_press_event", ms_ev)
		if event.button == gdk.BUTTON_PRIMARY and event.state & (gdk.ModifierType.BUTTON1_MASK | \
																 gdk.ModifierType.BUTTON2_MASK | \
																 gdk.ModifierType.BUTTON3_MASK | \
																 gdk.ModifierType.BUTTON4_MASK | \
																 gdk.ModifierType.BUTTON5_MASK) == 0:
			self.last_mousedown = event.copy()
		else:
			self.last_mousedown = None

		if __debug__: self.check_dom_events("button_press_event")


	def handle_button_release_event(self, drawingarea, event):
		if self.nodes_under_pointer:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			mouse_button = self.get_pressed_mouse_button(event)
			keys = self.get_keys(event)
			ms_ev = MouseEvent(	"mouseup", target=self.nodes_under_pointer[-1], \
								detail=self.current_click_count, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("button_release_event", ms_ev)
		if self.last_mousedown and self.check_click_hysteresis(self.last_mousedown, event):
			self.last_mousedown = None
			self.emit('clicked', event)
		else:
			self.last_mousedown = None

		if __debug__: self.check_dom_events("button_release_event")


	def handle_clicked(self, drawingarea, event):
		if self.nodes_under_pointer:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			mouse_button = self.get_pressed_mouse_button(event)
			keys = self.get_keys(event)
			ms_ev = MouseEvent(	"click", target=self.nodes_under_pointer[-1], \
								detail=self.current_click_count, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("clicked", ms_ev)
		if __debug__:
			print("clicked")

		if __debug__: self.check_dom_events("clicked")

	def emit_dom_event(self, handler, ms_ev):
		#~ print(handler, ms_ev)
		if __debug__:
			self.emitted_dom_events.append(ms_ev)

	if __debug__:
		def check_dom_events(self, handler):

			if handler == "motion_notify_event":
				#~ Mousemove
				assert if_(self.nodes_under_pointer, then=any(_ms_ev.type_ == "mousemove" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `nodes_under_pointer` are not empty, a DOM event `mousemove` should be emitted."
				assert if_(not self.nodes_under_pointer, then=all(_ms_ev.type_ != "mousemove" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `nodes_under_pointer` are empty, a DOM event `mousemove` should not be emitted."

				#~ Mouseleave
				assert if_(not self.nodes_under_pointer and self.previous_nodes_under_pointer, then=any(_ms_ev.type_ == "mouseleave" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `previous_nodes_under_pointer` are not empty and `nodes_under_pointer` are empty, a DOM event 'mouseleave` should be emitted"
				assert if_(self.nodes_under_pointer != self.previous_nodes_under_pointer and len(self.nodes_under_pointer)==len(self.previous_nodes_under_pointer), then=any(_ms_ev.type_ == "mouseleave" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `previous_nodes_under_pointer` are not equal `nodes_under_pointer` and contains equal number of items, a DOM event 'mouseleave` should be emitted"
				assert if_(len(self.nodes_under_pointer) < len(self.previous_nodes_under_pointer), then=any(_ms_ev.type_ == "mouseleave" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `nodes_under_pointer` contains less objects then `previous_nodes_under_pointer`, a DOM event 'mouseleave` should be emitted"
				assert if_(self.previous_nodes_under_pointer and self.previous_nodes_under_pointer[-1] not in self.nodes_under_pointer, then=any(_ms_ev.type_ == "mouseleave" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `nodes_under_pointer` not contains top `previous_nodes_under_pointer`, a DOM event 'mouseleave` should be emitted"
				assert if_(self.nodes_under_pointer and self.nodes_under_pointer == self.previous_nodes_under_pointer, then=any(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `nodes_under_pointer` is equal to `previous_nodes_under_pointer`, a DOM event 'mouseleave` should not be emitted"
				assert if_(self.nodes_under_pointer and not self.previous_nodes_under_pointer, then=all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `nodes_under_pointer` are not empty and `previous_nodes_under_pointer` are empty, a DOM event 'mouseleave` should not be emitted"

				#~ Mouseout
				assert if_(not self.previous_nodes_under_pointer and not self.nodes_under_pointer, then=all(_ms_ev.type_ != "mouseout" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseout` should not be emitted"


				#~ assert if_(self.nodes_under_pointer != self.previous_nodes_under_pointer and self.previous_nodes_under_pointer, then=any(_ms_ev.type_ == "mouseout" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `previous_nodes_under_pointer` are different to `nodes_under_pointer` and `previous_nodes_under_pointer`, a DOM event 'mouseout` should be emitted"
				#~ assert if_(self.nodes_under_pointer != self.previous_nodes_under_pointer and len(self.nodes_under_pointer)==len(self.previous_nodes_under_pointer), then=any(_ms_ev.type_ == "mouseout" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `previous_nodes_under_pointer` are different `nodes_under_pointer` are not empty, a DOM event 'mouseout` should not be emitted"
				#~ assert if_(len(self.nodes_under_pointer) < len(self.previous_nodes_under_pointer), then=any(_ms_ev.type_ == "mouseout" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `nodes_under_pointer` contains less objects then `previous_nodes_under_pointer`, a DOM event 'mouseout` should be emitted"
				#~ assert if_(self.previous_nodes_under_pointer and self.previous_nodes_under_pointer[-1] not in self.nodes_under_pointer, then=any(_ms_ev.type_ == "mouseout" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when top `previous_nodes_under_pointer` not belongs to `nodes_under_pointer`, a DOM event 'mouseout` should be emitted"

				#~ Mouseenter
				assert if_(self.nodes_under_pointer and not self.previous_nodes_under_pointer, then=any(_ms_ev.type_ == "mouseenter" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` are not empty, a DOM event 'mouseenter` should be emitted"
				assert if_(self.nodes_under_pointer != self.previous_nodes_under_pointer and (len(self.nodes_under_pointer)>=len(self.previous_nodes_under_pointer)), then=any(_ms_ev.type_ == "mousenter" for _ms_ev in self.emitted_dom_events)), "For a `motion_notify_event`, when `previous_nodes_under_pointer` are not equal `nodes_under_pointer` and `nodes_under_pointer` contains equal or more number of items, a DOM event 'mouseenter` should be emitted"

			self.emitted_dom_events.clear()
		#~ if self.previous_nodes_under_pointer != self.nodes_under_pointer:
			#~ if self.previous_nodes_under_pointer:

if __debug__:
	def if_(condition, then):
		if condition:
			return then
		else:
			return True



if __name__ == '__main__':
	import signal

	from gi.repository import GLib as glib

	glib.threads_init()

	css = gtk.CssProvider()
	css.load_from_path('gfx/style.css')
	gtk.StyleContext.add_provider_for_screen(gdk.Screen.get_default(), css, gtk.STYLE_PROVIDER_PRIORITY_USER)

	window = gtk.Window(gtk.WindowType.TOPLEVEL)
	window.set_name('main_window')

	svgwidget = SVGWidget()
	svgwidget.load_url('gfx/drawing.svg')
	window.add(svgwidget)

	window.show_all()

	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	window.connect('destroy', lambda window: mainloop.quit())

	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()



