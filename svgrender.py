#!/usr/bin/python3
#-*- coding: utf-8 -*-


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk

from domevents import *
import cairo

import cairosvg.surface
import cairosvg.parser

from enum import Enum


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
	EMPTY_SVG = b'''<?xml version="1.0" encoding="UTF-8"?>
		<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 1 1" width="1px" height="1px">
		</svg>
	'''
	class NodesUnderPointerRelation(Enum):
		CHANGED = 1
		EXIT = 2
		ENTER = 3
		MOVE = 4
		OUT = 5

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

		self.document = cairosvg.parser.Tree(bytestring=self.EMPTY_SVG)

		self.rendered_svg_surface = None
		self.nodes_under_pointer = []
		self.previous_nodes_under_pointer = []
		self.connect('configure-event', self.handle_configure_event)
		self.connect('draw', self.handle_draw)
		self.connect('motion-notify-event', self.handle_motion_notify_event)
		self.connect('button-press-event', self.handle_button_press_event)
		self.connect('button-release-event', self.handle_button_release_event)

		self.add_events(gdk.EventMask.POINTER_MOTION_MASK)
		self.add_events(gdk.EventMask.BUTTON_PRESS_MASK)
		self.add_events(gdk.EventMask.BUTTON_RELEASE_MASK)

	def load_url(self, url):
		self.document = cairosvg.parser.Tree(url=url)
		if self.get_realized():
			rect = self.get_allocation()
			self.rendered_svg_surface = self.SVGRenderBg.render(self.document, rect.width, rect.height)
		self.queue_draw()

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

	def get_nodes_relation_marks(self):
		marks = set()
		if self.previous_nodes_under_pointer != self.nodes_under_pointer:
			if self.previous_nodes_under_pointer and self.nodes_under_pointer:
				marks.add(self.NodesUnderPointerRelation.CHANGED)
			if self.previous_nodes_under_pointer:
				marks.add(self.NodesUnderPointerRelation.EXIT)
			if self.nodes_under_pointer:
				marks.add(self.NodesUnderPointerRelation.ENTER)
				marks.add(self.NodesUnderPointerRelation.MOVE)
		else:
			if self.previous_nodes_under_pointer:
				marks.add(self.NodesUnderPointerRelation.MOVE)
			else:
				marks.add(self.NodesUnderPointerRelation.OUT)
		return frozenset(marks)

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
		self.update_nodes_under_pointer(event)
		marks = self.get_nodes_relation_marks()
		if self.NodesUnderPointerRelation.OUT not in marks:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			keys = self.get_keys(event)
			if self.previous_nodes_under_pointer:
				previous_related_target = self.previous_nodes_under_pointer[-1]
			else:
				previous_related_target = None
			if self.NodesUnderPointerRelation.MOVE in marks:
				ms_ev = MouseEvent("mousemove", target=self.nodes_under_pointer[-1], \
								clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								buttons=mouse_buttons)
				print(ms_ev)
			if self.NodesUnderPointerRelation.ENTER in marks:
				ms_ev = MouseEvent("mouseover", target=self.nodes_under_pointer[-1], \
								clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								buttons=mouse_buttons, relatedTarget=previous_related_target)
				print(ms_ev)
				ms_ev = MouseEvent("mouseenter", target=self.nodes_under_pointer[-1], \
								clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								buttons=mouse_buttons, relatedTarget=previous_related_target)
				print(ms_ev)
			if self.NodesUnderPointerRelation.EXIT in marks:
				if self.nodes_under_pointer:
					new_target = self.nodes_under_pointer[-1]
				else:
					new_target = None
				ms_ev = MouseEvent("mouseout", target=new_target, \
								clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								buttons=mouse_buttons, relatedTarget=new_target)
				print(ms_ev)
				ms_ev = MouseEvent("mouseleave", target=new_target, \
								clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								buttons=mouse_buttons, relatedTarget=new_target)
				print(ms_ev)
		#canvas.queue_draw()

	def handle_button_press_event(self, drawingarea, event):
		if self.nodes_under_pointer:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			mouse_button = self.get_pressed_mouse_button(event)
			keys = self.get_keys(event)
			ms_ev = MouseEvent(	"mousedown", target=self.nodes_under_pointer[-1], \
								detail=1 , clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			print(ms_ev)

	def handle_button_release_event(self, drawingarea, event):
		if self.nodes_under_pointer:
			mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
			mouse_button = self.get_pressed_mouse_button(event)
			keys = self.get_keys(event)
			ms_ev = MouseEvent(	"mouseup", target=self.nodes_under_pointer[-1], \
								detail=1 , clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			print(ms_ev)

if __name__ == '__main__':
	import signal

	from gi.repository import GObject as gobject
	from gi.repository import GLib as glib

	glib.threads_init()

	css = gtk.CssProvider()
	css.load_from_path('gfx/style.css')
	gtk.StyleContext.add_provider_for_screen(gdk.Screen.get_default(), css, gtk.STYLE_PROVIDER_PRIORITY_USER)

	window = gtk.Window(gtk.WindowType.TOPLEVEL)
	window.set_name('main_window')

	svgwidget = SVGWidget()
	svgwidget.load_url('gfx/BYR_color_wheel.svg')
	window.add(svgwidget)

	window.show_all()

	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	window.connect('destroy', lambda window: mainloop.quit())

	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()








