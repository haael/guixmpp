#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'PointerView',


import gi
#gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

import cairo

if __name__ == '__main__':
	from guixmpp.domevents import MouseEvent
	from guixmpp.view.utils import *
else:
	from ..domevents import MouseEvent
	from .utils import *


class PointerView:
	def set_image(self, widget, image):
		widget.__pointed = []
	
	def get_pointed(self, widget):
		try:
			return widget.__pointed[-1]
		except IndexError:
			return None
	
	def get_buttons(self, widget):
		try:
			return frozenset(widget.__buttons)
		except AttributeError:
			return frozenset()
	
	def handle_event(self, widget, event, evtype, name):
		if name != 'motion' and name != 'button': return NotImplemented
		
		try:
			x = event.x
			y = event.y
			button = event.button
		except AttributeError:
			if len(event) == 3:
				button, x, y = event
			else:
				button = 0
				x, y = event
		
		if not hasattr(widget, '_PointerView__buttons'):
			widget.__buttons = set()
		
		if evtype == 'BUTTON_PRESS':
			widget.__buttons.add(button)
			self.update(widget)
		
		elif evtype == 'BUTTON_RELEASE':
			widget.__buttons.remove(button)
			self.update(widget)
		
		elif evtype == 'MOTION_NOTIFY':
			surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, (0, 0, self.get_viewport_width(widget), self.get_viewport_height(widget)))
			pointed, qx, qy = widget.poke_image(self, cairo.Context(surface), x, y)
			surface.finish()
			
			if pointed != widget.__pointed:
				old_pointed = self.get_pointed(widget)
				widget.__pointed = pointed
				new_pointed = self.get_pointed(widget)
				
				if old_pointed != new_pointed:
					if old_pointed is not None:
						dom_event = MouseEvent('mouseout', **pointer_position(event, qx, qy), **modifier_keys(self.get_modifier_keys(widget)), **pressed_mouse_buttons_mask(self.get_buttons(widget)))
						widget.emit('dom_event', dom_event, old_pointed)
					
					if old_pointed is not None and (new_pointed is None or not self.are_nodes_ordered(old_pointed, new_pointed)):
						dom_event = MouseEvent('mouseleave', **pointer_position(event, qx, qy), **modifier_keys(self.get_modifier_keys(widget)), **pressed_mouse_buttons_mask(self.get_buttons(widget)))
						widget.emit('dom_event', dom_event, old_pointed)
					
					if new_pointed is not None:
						dom_event = MouseEvent('mouseover', **pointer_position(event, qx, qy), **modifier_keys(self.get_modifier_keys(widget)), **pressed_mouse_buttons_mask(self.get_buttons(widget)))
						widget.emit('dom_event', dom_event, new_pointed)
					
					if new_pointed is not None and (old_pointed is None or not self.are_nodes_ordered(new_pointed, old_pointed)):
						dom_event = MouseEvent('mouseenter', **pointer_position(event, qx, qy), **modifier_keys(self.get_modifier_keys(widget)), **pressed_mouse_buttons_mask(self.get_buttons(widget)))
						widget.emit('dom_event', dom_event, new_pointed)
					
					self.update(widget)
			
			dom_event = MouseEvent('mousemove', **pointer_position(event, qx, qy), **modifier_keys(self.get_modifier_keys(widget)), **pressed_mouse_buttons_mask(self.get_buttons(widget)))
			widget.emit('dom_event', dom_event, self.get_pointed(widget))

