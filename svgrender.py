#!/usr/bin/python3
#-*- coding: utf-8 -*-


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import GLib as glib

from domevents import *
import cairo

import cairosvg.surface
import cairosvg.parser

from enum import Enum
from math import hypot

if __debug__:
	from collections import Counter
	import itertools

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
		'clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
		'dblclicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
	}

	EMPTY_SVG = b'''<?xml version="1.0" encoding="UTF-8"?>
		<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 1 1" width="1px" height="1px">
		</svg>
	'''

	CLICK_TIME = float("inf")
	CLICK_RANGE = 5
	DBLCLICK_TIME = float("inf")
	DBLCLICK_RANGE = 5
	COUNT_TIME = float("inf")
	COUNT_RANGE = 5

	class Keys(Enum):
		SHIFT = 1
		ALT = 2
		CTRL = 4
		META = 8

	def __init__(self):
		super().__init__()
		self.set_can_focus(True)

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
		self.last_mousedown = None
		self.first_click = None
		self.last_click = None
		self.current_click_count = 0
		self.last_keydown = None
		self.element_in_focus = self.document
		self.previous_focus = None
		
		self.connect('configure-event', self.handle_configure_event)
		self.connect('draw', self.handle_draw)
		
		#~Mouse
		self.connect('motion-notify-event', self.handle_motion_notify_event)
		self.connect('button-press-event', self.handle_button_press_event)
		self.connect('button-release-event', self.handle_button_release_event)
		self.connect('clicked', self.handle_clicked)
		self.connect('dblclicked', self.handle_dblclicked)
		
		#~Wheel
		self.connect("scroll-event", self.handle_scroll_event)
		
		#~Keyboard
		self.connect('key-press-event', self.handle_key_press_event)
		self.connect('key-release-event', self.handle_key_release_event)

		if __debug__: print("{:10} | {:10} | {:10}".format("Type", "Target", "relatedTarget"));
		self.add_events(gdk.EventMask.POINTER_MOTION_MASK)
		self.add_events(gdk.EventMask.BUTTON_RELEASE_MASK)
		self.add_events(gdk.EventMask.BUTTON_PRESS_MASK)
		
		self.add_events(gdk.EventMask.KEY_PRESS_MASK)
		self.add_events(gdk.EventMask.KEY_RELEASE_MASK)
		self.add_events(gdk.EventMask.SMOOTH_SCROLL_MASK)
		#~ print(dir(gdk.EventMask))

	def load_url(self, url):
		self.document = cairosvg.parser.Tree(url=url)
		self.element_in_focus = self.document
		if self.get_realized():
			rect = self.get_allocation()
			self.rendered_svg_surface = self.SVGRenderBg.render(self.document, rect.width, rect.height)
		self.queue_draw()

	@classmethod
	def check_dblclick_hysteresis(cls, press_event, event):
		if hypot(press_event.x - event.x, press_event.y - event.y) < cls.DBLCLICK_RANGE \
		   and (event.get_time() - press_event.get_time()) < cls.DBLCLICK_TIME:
			return True
		return False

	@classmethod
	def check_count_hysteresis(cls, press_event, event):
		if hypot(press_event.x - event.x, press_event.y - event.y) < cls.COUNT_RANGE \
		   and (event.get_time() - press_event.get_time()) < cls.COUNT_TIME:
			return True
		return False

	@classmethod
	def check_click_hysteresis(cls, press_event, event):
		if hypot(press_event.x - event.x, press_event.y - event.y) < cls.CLICK_RANGE \
		   and (event.get_time() - press_event.get_time()) < cls.CLICK_TIME:
			return True
		return False

	@classmethod
	def gen_node_parents(cls, node):
		if node.parent: #FIXME
			yield from cls.gen_node_parents(node.parent)
		yield node

	@classmethod
	def get_keys(cls, event):
		return {cls.Keys.SHIFT: bool(event.state & gdk.ModifierType.SHIFT_MASK),\
				cls.Keys.CTRL: bool(event.state & gdk.ModifierType.CONTROL_MASK),\
				cls.Keys.ALT: bool(event.state & (gdk.ModifierType.MOD1_MASK | gdk.ModifierType.MOD5_MASK)),\
				cls.Keys.META: bool(event.state & (gdk.ModifierType.META_MASK | gdk.ModifierType.SUPER_MASK | gdk.ModifierType.MOD4_MASK))}

	@classmethod
	def ancestors(cls, node):
		return frozenset(id(anc) for anc in cls.gen_node_parents(node))

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
		
	@staticmethod
	def get_key_location(keyval_name):
		if len(keyval_name) > 1:
			if keyval_name.endswith("R"):
				return KeyboardEvent.DOM_KEY_LOCATION_RIGHT
			elif keyval_name.endswith("L"):
				return KeyboardEvent.DOM_KEY_LOCATION_LEFT
			elif keyval_name.startswith("KP"):
				return KeyboardEvent.DOM_KEY_LOCATION_NUMPAD
			else:
				return KeyboardEvent.DOM_KEY_LOCATION_STANDARD
		else:
			return KeyboardEvent.DOM_KEY_LOCATION_STANDARD

	def set_dom_focus(self, element):
		if element_focusable and self.element_in_focus != self.previous_focus:
			self.previous_focus = self.element_in_focus
			self.element_in_focus = element

	def element_focusable(self, element):
		return True

	def update_nodes_under_pointer(self, event):
		self.previous_nodes_under_pointer = self.nodes_under_pointer[:]
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
		if __debug__:
			assert not self.emitted_dom_events
		
		if self.last_mousedown and not self.check_click_hysteresis(self.last_mousedown, event):
			self.last_mousedown = None
		
		self.update_nodes_under_pointer(event)
		
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		keys = self.get_keys(event)

		if self.previous_nodes_under_pointer != self.nodes_under_pointer:
			if self.previous_nodes_under_pointer:
				if self.nodes_under_pointer:
					if self.previous_nodes_under_pointer[-1] != self.nodes_under_pointer[-1]:
						ms_ev = MouseEvent("mouseout", target=self.previous_nodes_under_pointer[-1], \
											clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
											shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
											altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
											buttons=mouse_buttons, relatedTarget=self.nodes_under_pointer[-1])
						self.emit_dom_event("motion_notify_event", ms_ev)
						
						ms_ev = MouseEvent("mouseleave", target=self.previous_nodes_under_pointer[-1], \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons, relatedTarget=self.nodes_under_pointer[-1])
						self.emit_dom_event("motion_notify_event", ms_ev)
						
						#~ if __debug__:
							#~ pnup = self.ancestors(self.previous_nodes_under_pointer[-1])
							#~ nup = self.ancestors(self.nodes_under_pointer[-1])
							#~ print("pnup:", pnup)
							#~ print("nup:", nup)
							#~ print("pnup - nup:", pnup - nup)
							#~ print("nup - pnup:", nup - pnup)
				else:
					ms_ev = MouseEvent("mouseout", target=self.previous_nodes_under_pointer[-1], \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons)
					self.emit_dom_event("motion_notify_event", ms_ev)
					
					ms_ev = MouseEvent("mouseleave", target=self.previous_nodes_under_pointer[-1], \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons)
					self.emit_dom_event("motion_notify_event", ms_ev)

			if self.nodes_under_pointer:
				if self.previous_nodes_under_pointer:
					if self.previous_nodes_under_pointer[-1] != self.nodes_under_pointer[-1]:
						ms_ev = MouseEvent("mouseover", target=self.nodes_under_pointer[-1], \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons, relatedTarget=self.previous_nodes_under_pointer[-1])
						self.emit_dom_event("motion_notify_event", ms_ev)
						
						ms_ev = MouseEvent("mouseenter", target=self.nodes_under_pointer[-1], \
										clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
										shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
										altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
										buttons=mouse_buttons, relatedTarget=self.previous_nodes_under_pointer[-1])
						self.emit_dom_event("motion_notify_event", ms_ev)

				else:
					ms_ev = MouseEvent("mouseover", target=self.nodes_under_pointer[-1], \
									clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
									shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
									altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
									buttons=mouse_buttons)
					self.emit_dom_event("motion_notify_event", ms_ev)
					
					ms_ev = MouseEvent("mouseenter", target=self.nodes_under_pointer[-1], \
									clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
									shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
									altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
									buttons=mouse_buttons)
					self.emit_dom_event("motion_notify_event", ms_ev)
		
		if self.nodes_under_pointer:
			ms_ev = MouseEvent("mousemove", target=self.nodes_under_pointer[-1], \
							clientX=event.x, clientY=event.y, screenX=event.x_root, screenY=event.y_root, \
							shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
							altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
							buttons=mouse_buttons)
			self.emit_dom_event("motion_notify_event", ms_ev)

		#canvas.queue_draw()

		if __debug__:
			self.check_dom_events("motion_notify_event")
			assert not self.emitted_dom_events

	def handle_button_press_event(self, drawingarea, event):
		if event.button == gdk.BUTTON_PRIMARY and event.state & (gdk.ModifierType.BUTTON1_MASK | \
																 gdk.ModifierType.BUTTON2_MASK | \
																 gdk.ModifierType.BUTTON3_MASK | \
																 gdk.ModifierType.BUTTON4_MASK | \
																 gdk.ModifierType.BUTTON5_MASK) == 0:
			self.last_mousedown = event.copy()
		else:
			self.last_mousedown = None
		
		if self.first_click and not self.check_count_hysteresis(self.first_click, event):
			self.current_click_count = 0
			self.first_click = None
		
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)
		
		if self.nodes_under_pointer:
			ms_ev = MouseEvent(	"mousedown", target=self.nodes_under_pointer[-1], \
								detail=self.current_click_count+1, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("button_press_event", ms_ev)

		if __debug__: self.check_dom_events("button_press_event")

	def handle_button_release_event(self, drawingarea, event):
		if self.last_mousedown and self.check_click_hysteresis(self.last_mousedown, event):
			event_copy = event.copy()
			glib.idle_add(lambda: self.emit('clicked', event_copy) and False)

		if self.first_click and not self.check_count_hysteresis(self.first_click, event):
			self.current_click_count = 0
			self.first_click = None

		self.last_mousedown = None

		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)

		if self.nodes_under_pointer:
			mouseup_target = self.nodes_under_pointer[-1]
		else:
			mouseup_target = None
		ms_ev = MouseEvent(	"mouseup", target=mouseup_target, \
							detail=self.current_click_count+1, clientX=event.x, clientY=event.y, \
							screenX=event.x_root, screenY=event.y_root, \
							shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
							altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
							button=mouse_button, buttons=mouse_buttons)
		self.emit_dom_event("button_release_event", ms_ev)

		if __debug__: self.check_dom_events("button_release_event")

	def handle_clicked(self, drawingarea, event):
		if self.last_click and self.check_dblclick_hysteresis(self.last_click, event):
			event_copy = event.copy()
			glib.idle_add(lambda: self.emit('dblclicked', event_copy) and False)
			self.last_click = None
		else:
			self.last_click = event.copy()
		
		if self.first_click and self.check_count_hysteresis(self.first_click, event):
			self.current_click_count += 1
		else:
			self.current_click_count = 1
			self.first_click = event.copy()

		if self.nodes_under_pointer:
			glib.idle_add(lambda: self.set_dom_focus(self.nodes_under_pointer[-1]))
		else:
			glib.idle_add(lambda: self.set_dom_focus())

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

		if __debug__: self.check_dom_events("clicked")

	def handle_dblclicked(self, drawingarea, event):
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)

		if self.nodes_under_pointer:
			ms_ev = MouseEvent(	"dblclick", target=self.nodes_under_pointer[-1], \
								detail=self.current_click_count, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("dblclicked", ms_ev)
		
		if __debug__: self.check_dom_events("dblclicked")

	def handle_key_press_event(self, widget, event):
		print("Press", gdk.keyval_name(event.keyval))
		if self.last_keydown and self.last_keydown.keyval == event.keyval:
			repeated = True
		else:
			self.last_keydown = event.copy()
			repeated = False
		
		keyval_name = gdk.keyval_name(event.keyval)
		keys = self.get_keys(event)
		located = self.get_key_location(keyval_name)
		focused = self.element_in_focus
		kb_ev = KeyboardEvent(	"keydown", target=focused, \
								key=gdk.keyval_name(event.keyval), code=str(event.keyval), \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								location=located, repeat=repeated)
		self.emit_dom_event("key_pressed", kb_ev)
		
		if __debug__: self.check_dom_events("key_pressed")
	
	def handle_key_release_event(self, widget, event):
		print("Release", gdk.keyval_name(event.keyval))
		self.last_keydown = None
		
		keyval_name = gdk.keyval_name(event.keyval)
		keys = self.get_keys(event)
		located = self.get_key_location(keyval_name)
		focused = self.element_in_focus
		kb_ev = KeyboardEvent(	"keyup", target=focused, \
								key=gdk.keyval_name(event.keyval), code=str(event.keyval), \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								location=located)
		self.emit_dom_event("key_released", kb_ev)
		
		if __debug__: self.check_dom_events("key_released")

	def handle_scroll_event(self, widget, event):
		print("Scrolled")
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)
		if self.nodes_under_pointer:
			wheel_target = self.nodes_under_pointer[-1]
		else:
			wheel_target = None
			
		wh_ev = WheelEvent(	"wheel", target=wheel_target, \
							clientX=event.x, clientY=event.y, \
							screenX=event.x_root, screenY=event.y_root, \
							shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
							altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
							button=mouse_button, buttons=mouse_buttons, \
							deltaX=event.delta_x, deltaY=event.delta_y, \
							deltaMode=WheelEvent.DOM_DELTA_LINE)
			
		self.emit_dom_event("scrolled_event", wh_ev)

		if __debug__: self.check_dom_events("scrolled_event")

	def emit_dom_event(self, handler, ev):
		#~ print(handler, ev)
		if __debug__:
			#~MouseEvent
			#~ print("{:10} | {:10} | {:10}".format(ev.type_, ev.target.get('fill'), ev.relatedTarget.get('fill') if ev.relatedTarget else "None"));
			#~ print(ev.detail, self.current_click_count)
			#~KeyboardEvent
			if handler == "key_pressed":
				print(ev)
				#~ print("{:10} | {:10} | {:10} | {:10} | {:10} | {:10}".format(ev.type_, str(ev.target), str(ev.key), str(ev.code), str(ev.location), str(ev.repeat)))
			self.emitted_dom_events.append(ev)

	def reset_after_exception(self):
		if __debug__:
			self.emitted_dom_events.clear()

	if __debug__:
		def check_dom_events(self, handler):
			nup = self.nodes_under_pointer
			pnup = self.previous_nodes_under_pointer

			cnt = Counter((_ms_ev.type_, id(_ms_ev.target)) for _ms_ev in self.emitted_dom_events)
			if cnt:
				common, common_num = cnt.most_common(1)[0]
				assert common_num < 2, "For a DOM Event `{}`, shoudn't be emitted two events with equal target and type.".format(common[0])

			#~ Target
			assert all(_ms_ev.target != None for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("mouseover", "mouseout", "mouseenter","mouseleave", "mousedown", "click", "dblclick")), "For events of types `mouseover`, `mouseout`, `mouseenter`,`mouseleave`, `mousedown`, `click` and `dblclick` event target can't be None."
			assert all(nup and (_ms_ev.target == nup[-1]) for _ms_ev in self.emitted_dom_events if (_ms_ev.type_ == "mouseover")), "For events of type `mouseover`, event target should be top `nodes_under_pointer` element"
			assert all(nup and (_ms_ev.target in nup) for _ms_ev in self.emitted_dom_events if (_ms_ev.type_ == "mouseenter")), "For events of type `mouseenter`, event target should be in `nodes_under_pointer` elements"
			assert all(pnup and (_ms_ev.target == pnup[-1]) for _ms_ev in self.emitted_dom_events if (_ms_ev.type_ == "mouseout")), "For events of type `mouseout`, event target should be top `previous_nodes_under_pointer` element"
			assert all(pnup and (_ms_ev.target in pnup) for _ms_ev in self.emitted_dom_events if (_ms_ev.type_ == "mouseleave")), "For events of type `mouseleave`, event target should be in `previous_nodes_under_pointer` elements"
			assert all(nup and (_ms_ev.target == nup[-1]) for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("mousedown", "click", "dblclick")), "For event of types `mousedown`, `mouseup`, `click` and `dblclick, event target should be top `nodes_under_pointer` element"
			assert all(_ms_ev.target == nup[-1] for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseup") if nup else all(_ms_ev.target == None for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseup"), "For event of type `mouseup` event target should be None if fired out of window border, otherwise target should be top `nodes_under_pointer` if it is over element."
			assert all(_kb_ev.target == self.element_in_focus for _kb_ev in self.emitted_dom_events if _kb_ev.type_ in ("keydown", "keyup")), "For events of type `keydown` or `keyup`, event target should be self.document if no one element is focused."
			assert all(_wh_ev.target == nup[-1] for _wh_ev in self.emitted_dom_events if _wh_ev.type_ == "wheel") if nup else True, "For events of type `wheel`, event target should be top node under pointer."

			#~ Detail
			assert all(_ms_ev.detail == 0 for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("mouseenter", "mouseleave", "mousemove", "mouseout", "mouseover")), "For events of types: `mouseenter`, `mouseleave`, `mousemove`, `mouseout` or `mouseover`. `detail` value should be equal to 0."
			assert all(_ms_ev.detail > 0 for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("click", "dblclick", "mousedown", "mouseup")), "For events of types: `click`, `dblclick`, `mousedown` or `mouseup`. `detail` value should be higher then 0."
			assert all(_ms_ev.detail == self.current_click_count + 1 for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("mousedown", "mouseup")), "For events of types: `mousedown` or `mouseup`. `detail` value should be equal to `current_click_count` + 1."
			assert all(_ms_ev.detail == self.current_click_count for _ms_ev in self.emitted_dom_events if _ms_ev.type_ in ("click", "dblclick")), "For events of types: `click` or `dblclick`. `detail` value should be equal to `current_click_count`."
			assert all(_kb_ev.detail == 0 for _kb_ev in self.emitted_dom_events if _kb_ev.type_ in ("keydown", "keyup")), "For `key_pressed`, all events of type `keydown` or `keyup` should be emitted with default detail."

			#~ Mouse event order
			mouseout_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseout"]
			mouseleave_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseleave"]
			mouseover_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseover"]
			mouseenter_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mouseenter"]
			mousemove_events = [_ms_ev for _ms_ev in self.emitted_dom_events if _ms_ev.type_ == "mousemove"]

			for mouseout, mouseleave in itertools.product(mouseout_events, mouseleave_events):
				assert self.emitted_dom_events.index(mouseout) < self.emitted_dom_events.index(mouseleave), "For the appropriate Mouse Event order, events of type `mouseout` should happen before events of type `mouseleave`."
			for mouseleave, mouseover in itertools.product(mouseleave_events, mouseover_events):
				assert self.emitted_dom_events.index(mouseleave) < self.emitted_dom_events.index(mouseover), "For the appropriate Mouse Event order, events of type `mouseleave` should happen before events of type `mouseover`."
			for mouseover, mouseenter in itertools.product(mouseover_events, mouseenter_events):
				assert self.emitted_dom_events.index(mouseover) < self.emitted_dom_events.index(mouseenter), "For the appropriate Mouse Event order, events of type `mouseover` should happen before events of type `mouseenter`."
			for mouseenter, mousemove in itertools.product(mouseenter_events, mousemove_events):
				assert self.emitted_dom_events.index(mouseenter) < self.emitted_dom_events.index(mousemove), "For the appropriate Mouse Event order, events of type `mouseenter` should happen before events of type `mousemove`."

			#~ Repeat
			assert all(_kb_ev.repeat == False for _kb_ev in self.emitted_dom_events if _kb_ev.type_ == "keydown") if not self.last_keydown else True, "For event of type `keydown`, repeat attribute should be False if `last_keydown` not exist."
			assert all(_kb_ev.repeat == True for _kb_ev in self.emitted_dom_events if _kb_ev.type_ == "keydown" and self.last_keydown.keyval == _kb_ev.code) if self.last_keydown else True, "For event of type `keydown`, repeat attribute should be True if `last_keydown` exist and their `keyval` is equal to `KeyboardEvent.code`."
			assert all(_kb_ev.repeat == False for _kb_ev in self.emitted_dom_events if _kb_ev.type_ == "keyup"), "For event of type `keyup`, repeat attribute should be False."
			
			#~ Delta
			assert all(_wh_ev.deltaMode in (WheelEvent.DOM_DELTA_LINE, WheelEvent.DOM_DELTA_PAGE, WheelEvent.DOM_DELTA_PIXEL) for _wh_ev in self.emitted_dom_events if _wh_ev.type_ == "wheel"), "For event of type `wheel`, deltaMode should contain value from constants of WheelEvents."
			

			if handler == "motion_notify_event":
				moved_from_child_to_parent = (nup and pnup and nup[-1] != pnup[-1] and not (self.ancestors(nup[-1]) - self.ancestors(pnup[-1])))
				moved_from_parent_to_child = (nup and pnup and nup[-1] != pnup[-1] and not (self.ancestors(pnup[-1]) - self.ancestors(nup[-1])))
				
				#~ Mousemove
				assert any(_ms_ev.type_ == "mousemove" for _ms_ev in self.emitted_dom_events) if nup else True, "For a `motion_notify_event`, when `nodes_under_pointer` are not empty, a DOM event `mousemove` should be emitted."
				assert all(_ms_ev.type_ != "mousemove" for _ms_ev in self.emitted_dom_events) if not nup else True, "For a `motion_notify_event`, when `nodes_under_pointer` are empty, a DOM event `mousemove` should not be emitted."
				assert all(_ms_ev.type_ == "mousemove" for _ms_ev in self.emitted_dom_events) if (nup and pnup and (nup[-1] == pnup[-1])) else True, "For a `motion_notify_event` when the element under pointer hasn't changed, the only emitted DOM event shoud be `mousemove`."

				#~ Mouseleave
				assert all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events) if (not nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseleave` shouldn't be emitted"
				assert all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events) if (nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` aren't empty, a DOM event 'mouseleave` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseleave" for _ms_ev in self.emitted_dom_events) if (not nup and pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` aren't empty and `nodes_under_pointer` are empty, a DOM event 'mouseleave` should be emitted"
				assert all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] == pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are equal, a DOM event 'mouseleave` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseleave" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1] and not moved_from_parent_to_child) else True, "For `motion_notify_event`, when the pointer moved somewhere else than from parent to child, DOM event `mouseleave` should be emitted"
				assert all(_ms_ev.type_ != "mouseleave" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1] and moved_from_parent_to_child) else True, "For `motion_notify_event`, when the pointer moved from parent to child, DOM event `mouseleave` shouldn't be emitted"
				
				#~ Mouseout
				assert all(_ms_ev.type_ != "mouseout" for _ms_ev in self.emitted_dom_events) if (not nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseout` shouldn't be emitted"
				assert all(_ms_ev.type_ != "mouseout" for _ms_ev in self.emitted_dom_events) if (nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` aren't empty, a DOM event 'mouseout` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseout" for _ms_ev in self.emitted_dom_events) if (not nup and pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` aren't empty and `nodes_under_pointer` are empty, a DOM event 'mouseout` should be emitted"
				assert all(_ms_ev.type_ != "mouseout" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] == pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are equal, a DOM event 'mouseout` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseout" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are different, a DOM event 'mouseout` should be emitted"

				#~ Mouseenter
				assert all(_ms_ev.type_ != "mouseenter" for _ms_ev in self.emitted_dom_events) if (not nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseleave` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseenter" for _ms_ev in self.emitted_dom_events) if (nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` aren't empty, a DOM event 'mouseenter` should be emitted"
				assert all(_ms_ev.type_ != "mouseenter" for _ms_ev in self.emitted_dom_events) if (not nup and pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` aren't empty and `nodes_under_pointer` are empty, a DOM event 'mouseenter` should be emitted"
				assert all(_ms_ev.type_ != "mouseenter" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] == pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are equal, a DOM event 'mouseenter` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseenter" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1] and not moved_from_child_to_parent) else True, "For `motion_notify_event`, when the pointer moved somewhere else than from child to parent, DOM event `mouseenter` should be emitted"
				assert all(_ms_ev.type_ != "mouseenter" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1] and moved_from_child_to_parent) else True, "For `motion_notify_event`, when the pointer moved from child to parent, DOM event `mouseenter` shouldn't be emitted"

				#~Mouseover
				assert all(_ms_ev.type_ != "mouseover" for _ms_ev in self.emitted_dom_events) if (not nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` and `nodes_under_pointer` are empty, a DOM event 'mouseover` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseover" for _ms_ev in self.emitted_dom_events) if (nup and not pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` are empty and `nodes_under_pointer` aren't empty, a DOM event 'mouseover` should be emitted"
				assert all(_ms_ev.type_ != "mouseover" for _ms_ev in self.emitted_dom_events) if (not nup and pnup) else True, "For a `motion_notify_event`, when `previous_nodes_under_pointer` aren't empty and `nodes_under_pointer` are empty, a DOM event 'mouseover` should be emitted"
				assert all(_ms_ev.type_ != "mouseover" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] == pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are equal, a DOM event 'mouseover` shouldn't be emitted"
				assert any(_ms_ev.type_ == "mouseover" for _ms_ev in self.emitted_dom_events) if (nup and pnup and nup[-1] != pnup[-1]) else True, "For a `motion_notify_event`, when top `previous_nodes_under_pointer` and top `nodes_under_pointer` are different, a DOM event 'mouseover` should be emitted"

			elif handler == "button_press_event":
				assert all(_ms_ev.type_ == "mousedown" for _ms_ev in self.emitted_dom_events), "For `button_press_event`, only event of type `mousedown` should be emitted."

			elif handler == "button_release_event":
				assert all(_ms_ev.type_ == "mouseup" for _ms_ev in self.emitted_dom_events), "For `button_release_event`, only event of type `mouseup` should be emitted."

			elif handler == "clicked":
				assert all(_ms_ev.type_ == "click" for _ms_ev in self.emitted_dom_events), "For `clicked`, only event of type `click` should be emitted."
				assert any(_ms_ev.type_ == "click" for _ms_ev in self.emitted_dom_events) if nup else True, "For `clicked`, any event of type `click` should be emitted."

			elif handler == "dblclicked":
				assert all(_ms_ev.type_ == "dblclick" for _ms_ev in self.emitted_dom_events), "For `dblclicked`, only event of type `dblclick` should be emitted."
				assert any(_ms_ev.type_ == "dblclick" for _ms_ev in self.emitted_dom_events) if nup else True, "For `dblclicked`, any event of type `dblclick` should be emitted."
				
			elif handler == "key_pressed":
				assert all(_kb_ev.type_ == "keydown" for _kb_ev in self.emitted_dom_events), "For `key_pressed`, only event of type `keydown` should be emitted."
				assert any(_kb_ev.type_ == "keydown" for _kb_ev in self.emitted_dom_events), "For `key_pressed`, any event of type `keydown` should be emitted."
			
			elif handler == "key_released":
				assert all(_kb_ev.type_ == "keyup" for _kb_ev in self.emitted_dom_events), "For `key_released`, only event of type `keyup` should be emitted."
				assert any(_kb_ev.type_ == "keyup" for _kb_ev in self.emitted_dom_events), "For `key_released`, any event of type `keyup` should be emitted."
			
			elif handler == "scrolled_event":
				assert all(_wh_ev.type_ == "wheel" for _wh_ev in self.emitted_dom_events), "For `scrolled_event`, only event of type `wheel` should be emitted."
				assert any(_wh_ev.type_ == "wheel" for _wh_ev in self.emitted_dom_events), "For `scrolled_event`, any event of type `wheel` should be emitted."

			self.emitted_dom_events.clear()

if __name__ == '__main__':
	import signal
	import sys

	glib.threads_init()

	css = gtk.CssProvider()
	css.load_from_path('gfx/style.css')
	gtk.StyleContext.add_provider_for_screen(gdk.Screen.get_default(), css, gtk.STYLE_PROVIDER_PRIORITY_USER)

	window = gtk.Window(gtk.WindowType.TOPLEVEL)
	window.set_name('main_window')

	svgwidget = SVGWidget()
	#~ svgwidget.load_url('gfx/BYR_color_wheel.svg')
	svgwidget.load_url('gfx/drawing.svg')
	#~ svgwidget.load_url('gfx/drawing_no_white_BG.svg')
	window.add(svgwidget)

	window.show_all()

	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	sys.excepthook = lambda x, y, z: (sys.__excepthook__(x, y, z), svgwidget.reset_after_exception())
	window.connect('destroy', lambda window: mainloop.quit())

	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()



