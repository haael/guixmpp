#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'SVGWidget',


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import GLib as glib

from domevents import *
from svgrender import SVGRender

import cairo

from xml.etree.ElementTree import ElementTree, fromstring

from enum import Enum
from math import hypot

if __debug__:
	from collections import Counter
	import itertools



class SVGWidget(gtk.DrawingArea):
	__gsignals__ = {
		'clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
		'dblclicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
		'request_url': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))
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
	
	class ExtSVGRender(SVGRender):
		def __init__(self, parent):
			super().__init__()
			self.parent = parent
		
		#def request_url(self, url):
		#	glib.idle_add(lambda: self.parent.emit('request_url', url) and False)
		
		#def request_url(self, url):
		#	print("request_url", url)
		#	if url.startswith('data:'):
		#		self.register_err(url, "not supported")
		#	elif url == 'espresso.svg':
		#		super().request_url('gfx/' + url)
		#		#self.register_svg(url, self.get_document('gfx/' + url))
		#	else:
		#		super().request_url(url)
		
		def svg_update(self):
			self.parent.reset_state()
			self.parent.document = self.svg_get_document()
			self.parent.queue_draw()
			self.parent.synthesize_events()
	
	def reset_state(self):
		self.document = fromstring(self.EMPTY_SVG)
		self.rendered_svg_surface = None
		self.nodes_under_pointer = []
		self.previous_nodes_under_pointer = []
		self.last_mousedown = None
		self.last_mousedown_target = None
		self.first_click = None
		self.last_click = None
		self.current_click_count = 0
		self.last_keydown = None
		self.element_in_focus = self.document
		self.previous_focus = None
		self.pointer = None
	
	def __init__(self):
		super().__init__()
		self.set_can_focus(True)
		
		if __debug__:
			self.emitted_dom_events = list()
		
		self.reset_state()
		
		self.svgrender = self.ExtSVGRender(self)
		self.rendered_svg_surface = None
		
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
		
		#if __debug__: print("{:10} | {:10} | {:10}".format("Type", "Target", "relatedTarget"));
		self.add_events(gdk.EventMask.POINTER_MOTION_MASK)
		self.add_events(gdk.EventMask.BUTTON_RELEASE_MASK)
		self.add_events(gdk.EventMask.BUTTON_PRESS_MASK)
		
		self.add_events(gdk.EventMask.KEY_PRESS_MASK)
		self.add_events(gdk.EventMask.KEY_RELEASE_MASK)
		self.add_events(gdk.EventMask.SMOOTH_SCROLL_MASK)
		#~ print(dir(gdk.EventMask))
	
	def show_svg(self, url):
		self.svgrender.clear()
		self.svgrender.open(url)
	
	def xml_nodes(self, node=None):
		if node == None:
			node = self.document
		for child in node:
			yield from self.xml_nodes(child)
		yield node
	
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
	
	def gen_node_parents(self, node):
		#if node in self.child_parent_cache:
		#	yield from self.gen_node_parents(self.child_parent_cache[node])
		parent = node.findall('..')
		if parent:
			self.gen_node_parents(parent[0])
		yield node
	
	@classmethod
	def get_keys(cls, event):
		return {cls.Keys.SHIFT: bool(event.state & gdk.ModifierType.SHIFT_MASK),\
				cls.Keys.CTRL: bool(event.state & gdk.ModifierType.CONTROL_MASK),\
				cls.Keys.ALT: bool(event.state & (gdk.ModifierType.MOD1_MASK | gdk.ModifierType.MOD5_MASK)),\
				cls.Keys.META: bool(event.state & (gdk.ModifierType.META_MASK | gdk.ModifierType.SUPER_MASK | gdk.ModifierType.MOD4_MASK))}
	
	def ancestors(self, node):
		return frozenset(id(anc) for anc in self.gen_node_parents(node))
	
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
	
	def synthesize_events(self):
		pass # TODO
	
	def set_dom_focus(self, element):
		if self.element_in_focus is self.document:
			
			fc_ev = FocusEvent(	"focusin", target=element)
			self.emit_dom_event("focus_changed_event", fc_ev)
			
			self.element_in_focus = element
			
			fc_ev = FocusEvent( "focus", target=element)
			self.emit_dom_event("focus_changed_event", fc_ev)
		
		elif element != self.element_in_focus:
			
			fc_ev = FocusEvent(	"focusout", target=self.element_in_focus, relatedTarget=element)
			self.emit_dom_event("focus_changed_event", fc_ev)
			
			fc_ev = FocusEvent(	"focusin", target=element, relatedTarget=self.element_in_focus)
			self.emit_dom_event("focus_changed_event", fc_ev)
			
			self.previous_focus = self.element_in_focus
			self.element_in_focus = element
			
			fc_ev = FocusEvent(	"blur", target=self.previous_focus, relatedTarget=self.element_in_focus)
			self.emit_dom_event("focus_changed_event", fc_ev)
			
			fc_ev = FocusEvent(	"focus", target=self.element_in_focus, relatedTarget=self.previous_focus)
			self.emit_dom_event("focus_changed_event", fc_ev)
		
		if __debug__: self.check_dom_events("focus_changed_event")
	
	def change_dom_focus_next(self):
		iterator = (i for i in self.xml_nodes() if self.is_element_focusable(i))
		previous_id = id(next(iterator))
		focused_id = id(self.element_in_focus)
		for item in iterator:
			if previous_id == focused_id:
				glib.idle_add(lambda: self.set_dom_focus(item))
				break
			else:
				previous_id = id(item)
		else:
			glib.idle_add(lambda: self.set_dom_focus(next(i for i in self.xml_nodes() if self.is_element_focusable(i))))
	
	def change_dom_focus_prev(self):
		iterator = (i for i in self.xml_nodes() if self.is_element_focusable(i))
		previous_element = next(iterator)
		focused_id = id(self.element_in_focus)
		for item in iterator:
			actual_id = id(item)
			if actual_id == focused_id:
				glib.idle_add(lambda: self.set_dom_focus(previous_element))
				break
			else:
				previous_element = item
		else:
			glib.idle_add(lambda: self.set_dom_focus(previous_element))
	
	def is_element_focusable(self, element):
		return True
	
	def is_focused(self, element):
		return self.element_in_focus == element
	
	def render(self):
		if self.pointer:
			self.previous_nodes_under_pointer = self.nodes_under_pointer[:]
		
		rect = self.get_allocation()
		
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, None)
		context = cairo.Context(surface)
		
		context.set_source_rgb(1, 1, 1)
		context.paint() # background
		
		nodes_under_pointer = self.svgrender.render(context, (0, 0, rect.width, rect.height), pointer=self.pointer)
		
		if self.pointer:
			self.nodes_under_pointer = nodes_under_pointer
		assert self.nodes_under_pointer != None
		
		if self.rendered_svg_surface != None:
			self.rendered_svg_surface.finish()
		self.rendered_svg_surface = surface
	
	def update_nodes_under_pointer(self, event):
		self.pointer = event.x, event.y
		
		if self.pointer:
			self.previous_nodes_under_pointer = self.nodes_under_pointer[:]
		
		rect = self.get_allocation()
		
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, None)
		context = cairo.Context(surface)
		
		nodes_under_pointer = self.svgrender.hover(context, (0, 0, rect.width, rect.height), pointer=self.pointer)
		
		if self.pointer:
			self.nodes_under_pointer = nodes_under_pointer
		assert self.nodes_under_pointer != None
	
	def handle_configure_event(self, drawingarea, event):
		self.render()
	
	def handle_draw(self, drawingarea, ctx):
		if self.rendered_svg_surface == None:
			self.render()
		ctx.set_source_surface(self.rendered_svg_surface)
		ctx.paint()
	
	def handle_motion_notify_event(self, drawingarea, event):
		if __debug__:
			assert not self.emitted_dom_events
		
		if self.last_mousedown and not self.check_click_hysteresis(self.last_mousedown, event):
			self.last_mousedown = None
			self.last_mousedown_target = None
		
		self.update_nodes_under_pointer(event)
		
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		keys = self.get_keys(event)
		
		if self.previous_nodes_under_pointer != self.nodes_under_pointer:
			self.queue_draw()
			
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
			self.last_mousedown_target = None
		
		if self.first_click and not self.check_count_hysteresis(self.first_click, event):
			self.current_click_count = 0
			self.first_click = None
		
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)
		
		try:
			mousedown_target = self.nodes_under_pointer[-1]
		except IndexError:
			mousedown_target = None
		
		if mousedown_target != None:
			ms_ev = MouseEvent(	"mousedown", target=mousedown_target, \
								detail=self.current_click_count+1, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("button_press_event", ms_ev)
		
		self.last_mousedown_target = mousedown_target
		
		if __debug__: self.check_dom_events("button_press_event")
	
	def handle_button_release_event(self, drawingarea, event):
		if self.last_mousedown and self.check_click_hysteresis(self.last_mousedown, event):
			event_copy = event.copy()
			glib.idle_add(lambda: self.emit('clicked', event_copy) and False)
		
		if self.first_click and not self.check_count_hysteresis(self.first_click, event):
			self.current_click_count = 0
			self.first_click = None
		
		mouse_buttons = self.get_pressed_mouse_buttons_mask(event)
		mouse_button = self.get_pressed_mouse_button(event)
		keys = self.get_keys(event)
		
		if self.last_mousedown_target != None:
			try:
				mouseup_target = self.nodes_under_pointer[-1]
			except IndexError:
				mouseup_target = None
			ms_ev = MouseEvent(	"mouseup", target=mouseup_target, \
								detail=self.current_click_count+1, clientX=event.x, clientY=event.y, \
								screenX=event.x_root, screenY=event.y_root, \
								shiftKey=keys[self.Keys.SHIFT], ctrlKey=keys[self.Keys.CTRL], \
								altKey=keys[self.Keys.ALT], metaKey=keys[self.Keys.META], \
								button=mouse_button, buttons=mouse_buttons)
			self.emit_dom_event("button_release_event", ms_ev)
		
		self.last_mousedown = None
		self.last_mousedown_target = None
		
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
		
		if self.nodes_under_pointer and self.is_element_focusable(self.nodes_under_pointer[-1]) and not (self.is_focused(self.nodes_under_pointer[-1])):
			glib.idle_add(lambda: self.set_dom_focus(self.nodes_under_pointer[-1]))
		
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
		#print("Press", gdk.keyval_name(event.keyval))
		if self.last_keydown and self.last_keydown.keyval == event.keyval:
			repeated = True
		else:
			self.last_keydown = event.copy()
			repeated = False
		
		if gdk.keyval_name(event.keyval).endswith("Tab"):
			if event.state & gdk.ModifierType.SHIFT_MASK:
				glib.idle_add(lambda: self.change_dom_focus_prev())
			else:
				glib.idle_add(lambda: self.change_dom_focus_next())
		
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
		#print("Release", gdk.keyval_name(event.keyval))
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
		#print("Scrolled")
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
							deltaX=event.delta_x, deltaY=event.delta_y, \
							deltaMode=WheelEvent.DOM_DELTA_LINE)
		
		self.emit_dom_event("scrolled_event", wh_ev)
		
		if __debug__: self.check_dom_events("scrolled_event")
	
	def emit_dom_event(self, handler, ev):
		#print(ev.type_, ev.target['id'] if hasattr(ev, 'target') and ('id' in ev.target) else "")
		try:
			print(ev.type_, '#'.join((ev.target.tag, ev.target.get('id'))) if hasattr(ev, 'target') else None)
		except (TypeError, AttributeError):
			print(ev.type_, ev.target, '#None')
		if __debug__:
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
			assert all(self.is_element_focusable(_fc_ev.target) for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focusin"), "Focus Event target of type `focusin` should be focusable"
			assert all(self.is_element_focusable(_fc_ev.target) for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focusout"), "Focus Event target of type `focusout` should be focusable"
			assert all(self.is_element_focusable(_fc_ev.target) for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focus"), "Focus Event target of type `focus` should be focusable"
			assert all(self.is_element_focusable(_fc_ev.target) for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "blur"), "Focus Event target of type `blur` should be focusable"
			
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
			
			# Focus event order
			focusin_event = [_fc_ev for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focusin"]
			focusout_event = [_fc_ev for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focusout"]
			focus_event = [_fc_ev for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "focus"]
			blur_event = [_fc_ev for _fc_ev in self.emitted_dom_events if _fc_ev.type_ == "blur"]
			
			for focusin, focus in zip(focusin_event, focus_event):
				assert self.emitted_dom_events.index(focusin) < self.emitted_dom_events.index(focus), "For the appropriate Focus Event order, events of type `focusin` should happen before events of type `focus`."
			for focusout, blur in zip(focusout_event, blur_event):
				assert self.emitted_dom_events.index(focusout) < self.emitted_dom_events.index(blur), "For the appropriate Focus Event order, events of type `focusout` should happen before events of type `blur`."
			for focusin, focus in zip(focusin_event, blur_event):
				assert self.emitted_dom_events.index(focusin) < self.emitted_dom_events.index(blur), "For the appropriate Focus Event order, events of type `focusin` should happen before events of type `blur`."
			for focusout, blur in zip(focusout_event, focus_event):
				assert self.emitted_dom_events.index(focusout) < self.emitted_dom_events.index(focus), "For the appropriate Focus Event order, events of type `focusout` should happen before events of type `focus`."
			
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

			elif handler == "focus_changed_event":
				assert any(_fc_ev.type_ == "focusin" for _fc_ev in self.emitted_dom_events) if self.is_element_focusable(self.element_in_focus) else True, "For `focus_change_event`, any event of type `focusin` should be emitted. When top `nodes_under_pointer` is focusable."
				assert any(_fc_ev.type_ == "focusout" for _fc_ev in self.emitted_dom_events) if self.is_element_focusable(self.element_in_focus) and self.previous_focus else True, "For `focus_change_event`, any event of type `focusout` should be emitted. When top `nodes_under_pointer` is focusable."
				assert any(_fc_ev.type_ == "focus" for _fc_ev in self.emitted_dom_events) if self.is_element_focusable(self.element_in_focus) else True, "For `focus_change_event`, any event of type `focus` should be emitted. When top `nodes_under_pointer` is focusable."
				assert any(_fc_ev.type_ == "blur" for _fc_ev in self.emitted_dom_events) if self.is_element_focusable(self.element_in_focus) and self.previous_focus else True, "For `focus_change_event`, any event of type `blur` should be emitted. When top `nodes_under_pointer` is focusable."
				
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
	#svgwidget.show_svg('gfx/acid1.svg')
	#svgwidget.show_svg('gfx/arcs_0.svg') # OK
	#svgwidget.show_svg('gfx/arcs_1.svg') # OK
	#svgwidget.show_svg('gfx/arcs_2.svg') # text
	#svgwidget.show_svg('gfx/BYR_color_wheel.svg') # OK
	#svgwidget.show_svg('gfx/Circulatory system SMIL.svg')
	#svgwidget.show_svg('gfx/Comparison of several satellite navigation system orbits.svg')
	#svgwidget.show_svg('gfx/Contra-zoom aka dolly zoom animation.svg')
	#svgwidget.show_svg('gfx/drawing.svg') # OK
	#svgwidget.show_svg('gfx/drawing_no_white_BG.svg') # OK
	#svgwidget.show_svg('gfx/ECB_encryption.svg') # text anchor
	#svgwidget.show_svg('gfx/espresso.svg')
	#svgwidget.show_svg('gfx/epicyclic gearing animation.svg') # text anchor
	#svgwidget.show_svg('gfx/fcGold Token.svg') # bezier
	#svgwidget.show_svg('gfx/genesis_pepe.svg') # OK
	#svgwidget.show_svg('gfx/Glutamic_acid_test.svg') # text anchor, clipPath
	#svgwidget.show_svg('gfx/gradient_france.svg') # OK
	#svgwidget.show_svg('gfx/gradient_linear.svg') # OK
	#svgwidget.show_svg('gfx/gradient_radial.svg')
	#svgwidget.show_svg('gfx/gradient_rainbow.svg') # OK
	#svgwidget.show_svg('gfx/Hamming(7,4)_example_1100.svg') # text
	#svgwidget.show_svg('gfx/History_of_the_Universe-zh-hant.svg')
	#svgwidget.show_svg('gfx/Homo_sapiens_lineage.svg') # gradient transform
	#svgwidget.show_svg('gfx/Letters_SVG.svg') # radial gradient
	#svgwidget.show_svg('gfx/logo_nocss.svg') # OK
	#svgwidget.show_svg('gfx/Morphing SMIL.svg') # blur
	#svgwidget.show_svg('gfx/PageRanks-Example.svg') # radial gradient
	#svgwidget.show_svg('gfx/Phonetics Guide.svg') # text anchor
	#svgwidget.show_svg('gfx/status_icons.svg') # OK
	#svgwidget.show_svg('gfx/Steering_wheel_1.svg') # OK
	#svgwidget.show_svg('gfx/Steering_wheel_2.svg') # gradient transform
	#svgwidget.show_svg('gfx/SVG_Blur_sample.svg') # blur
	#svgwidget.show_svg('gfx/SVG_logo.svg') # OK
	#svgwidget.show_svg('gfx/targets.svg') # OK
	#svgwidget.show_svg('gfx/Text_background_edge.svg')
	#svgwidget.show_svg('gfx/typographer_caps.svg') # bezier
	#svgwidget.show_svg('gfx/Vector-based_example.svg') # radial gradient
	svgwidget.show_svg('gfx/xforms_sample.svg')
	
	window.add(svgwidget)
	
	window.show_all()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	def exception_hook(exception, y, z):
		sys.__excepthook__(exception, y, z)
		#errorbox = gtk.MessageDialog(window, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.CLOSE, str(exception))
		#errorbox.run()
		#errorbox.destroy()
		svgwidget.reset_after_exception()
	
	sys.excepthook = lambda *args: exception_hook(*args)
	window.connect('destroy', lambda window: mainloop.quit())

	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()


