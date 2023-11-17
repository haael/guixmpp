#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'PointerView',


import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

from domevents import MouseEvent

from view.utils import *


class PointerView:
	def set_image(self, widget, image):
		widget.__pointed = []
	
	def get_pointed(self, widget):
		try:
			return widget.__pointed[-1]
		except IndexError:
			return None
	
	def handle_event(self, widget, event, name):
		if name != 'motion' and name != 'button': return NotImplemented
		
		if event.type == Gdk.EventType.MOTION_NOTIFY:
			pointed, qx, qy = widget.poke_image(event.x, event.y)
			
			if pointed != widget.__pointed:
				old_pointed = self.get_pointed(widget)
				widget.__pointed = pointed
				new_pointed = self.get_pointed(widget)
				
				if old_pointed != new_pointed:
					if old_pointed is not None:
						dom_event = MouseEvent('mouseout', target=old_pointed, **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
						widget.emit('dom_event', dom_event)
					
					if old_pointed is not None and (new_pointed is None or not self.are_nodes_ordered(old_pointed, new_pointed)):
						dom_event = MouseEvent('mouseleave', target=old_pointed, **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
						widget.emit('dom_event', dom_event)
					
					if new_pointed is not None:
						dom_event = MouseEvent('mouseover', target=new_pointed, **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
						widget.emit('dom_event', dom_event)
					
					if new_pointed is not None and (old_pointed is None or not self.are_nodes_ordered(new_pointed, old_pointed)):
						dom_event = MouseEvent('mouseenter', target=new_pointed, **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
						widget.emit('dom_event', dom_event)
					
					self.update(widget)
			
			dom_event = MouseEvent('mousemove', target=self.get_pointed(widget), **pointer_position(event, qx, qy), **modifier_keys(event), **pressed_mouse_buttons_mask(event))
			widget.emit('dom_event', dom_event)

