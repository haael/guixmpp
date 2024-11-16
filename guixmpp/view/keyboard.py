#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'KeyboardView',


import gi
#gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

if __name__ == '__main__':
	from guixmpp.domevents import KeyboardEvent
	from guixmpp.view.utils import *
else:
	from ..domevents import KeyboardEvent
	from .utils import *


def key_location(keyval_name):
	if len(keyval_name) > 1:
		if keyval_name.endswith('R'):
			location = KeyboardEvent.DOM_KEY_LOCATION_RIGHT
		elif keyval_name.endswith('L'):
			location = KeyboardEvent.DOM_KEY_LOCATION_LEFT
		elif keyval_name.startswith('KP'):
			location = KeyboardEvent.DOM_KEY_LOCATION_NUMPAD
		else:
			location = KeyboardEvent.DOM_KEY_LOCATION_STANDARD
	else:
		location = KeyboardEvent.DOM_KEY_LOCATION_STANDARD
	
	return {'location': location}


class KeyboardView:
	def set_image(self, widget, image):
		widget.__focus = None
		widget.__last_keyval = None
	
	def get_focus(self, widget):
		return widget.__focus
	
	def set_focus(self, widget, element):
		widget.__focus = element
		self.update(widget)
	
	def focus_next(self, widget):
		raise NotImplementedError
	
	def focus_previous(self, widget):
		raise NotImplementedError
	
	def handle_event(self, widget, event, name):
		if name != 'key': return NotImplemented
		
		if event.type == Gdk.EventType.KEY_PRESS:
			keyval_name = Gdk.keyval_name(event.keyval)
			dom_event = KeyboardEvent('keydown', key=event.string, code=keyval_name, repeat=(widget.__last_keyval == event.keyval), **key_location(keyval_name), **modifier_keys(event))
			widget.emit('dom_event', dom_event, self.get_focus(widget))
			widget.__last_keyval = event.keyval
		
		elif event.type == Gdk.EventType.KEY_RELEASE:
			keyval_name = Gdk.keyval_name(event.keyval)
			dom_event = KeyboardEvent('keyup', key=event.string, code=keyval_name, **key_location(keyval_name), **modifier_keys(event))
			widget.emit('dom_event', dom_event, self.get_focus(widget))
			widget.__last_keyval = None

