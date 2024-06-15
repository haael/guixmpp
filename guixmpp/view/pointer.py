#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'PointerView',


import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

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
	
	def handle_event(self, widget, event, name):
		if name != 'motion' and name != 'button': return NotImplemented
		
		if event.type == Gdk.EventType.BUTTON_PRESS:
			try:
				widget.__buttons.add(event.button)
			except AttributeError:
				widget.__buttons = set()
				widget.__buttons.add(event.button)
			self.update(widget)
		
		elif event.type == Gdk.EventType.BUTTON_RELEASE:
			try:
				widget.__buttons.remove(event.button)
			except (AttributeError, IndexError):
				pass
			self.update(widget)
		
		elif event.type == Gdk.EventType.MOTION_NOTIFY:
			pointed, qx, qy = widget.poke_image(self, event.x, event.y)
			
			if pointed != widget.__pointed:
				old_pointed = self.get_pointed(widget)
				widget.__pointed = pointed
				new_pointed = self.get_pointed(widget)
				
				if old_pointed != new_pointed:
					if old_pointed is not None:
						dom_event = MouseEvent('mouseout', **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
						widget.emit('dom_event', dom_event, old_pointed)
					
					if old_pointed is not None and (new_pointed is None or not self.are_nodes_ordered(old_pointed, new_pointed)):
						dom_event = MouseEvent('mouseleave', **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
						widget.emit('dom_event', dom_event, old_pointed)
					
					if new_pointed is not None:
						dom_event = MouseEvent('mouseover', **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
						widget.emit('dom_event', dom_event, new_pointed)
					
					if new_pointed is not None and (old_pointed is None or not self.are_nodes_ordered(new_pointed, old_pointed)):
						dom_event = MouseEvent('mouseenter', **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
						widget.emit('dom_event', dom_event, new_pointed)
					
					self.update(widget)
			
			dom_event = MouseEvent('mousemove', **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
			widget.emit('dom_event', dom_event, self.get_pointed(widget))

