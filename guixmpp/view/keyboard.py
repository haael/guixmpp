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
	def get_focus(self, widget):
		try:
			return widget.__focus
		except AttributeError:
			return None
	
	def set_focus(self, widget, element):
		widget.__focus = element
		self.update(widget)
	
	def focus_next(self, widget):
		raise NotImplementedError
	
	def focus_previous(self, widget):
		raise NotImplementedError
	
	def get_modifier_keys(self, widget):
		try:
			return widget.__modifier_keys
		except AttributeError:
			return 0
	
	def get_pressed_keys(self, widget):
		try:
			return widget.__pressed_keys
		except AttributeError:
			return frozenset()
	
	def handle_event(self, widget, event, evtype, name):
		if name != 'key': return NotImplemented
		
		try:
			string = event.string
			keyval = event.keyval
			modifiers = event.state
			keyval_name = Gdk.keyval_name(keyval)
		except AttributeError:
			if len(event) == 3:
				keyval, keycode, modifiers = event
				string = Gdk.keyval_to_unicode(keyval)
				keyval_name = Gdk.keyval_name(keyval)
			else:
				modifiers, = event
				string = ""
				keyval_name = ""
		
		if not hasattr(widget, '_KeyboardView__pressed_keys'):
			widget.__pressed_keys = set()
		
		if evtype == 'KEY_PRESS':
			widget.__modifier_keys = modifiers
			dom_event = KeyboardEvent('keydown', key=string, code=keyval_name, repeat=(keyval in self.get_pressed_keys(widget)), **key_location(keyval_name), **modifier_keys(self.get_modifier_keys(widget)))
			widget.__pressed_keys.add(keyval)
			widget.emit('dom_event', dom_event, self.get_focus(widget))
		
		elif evtype == 'KEY_RELEASE':
			widget.__modifier_keys = modifiers
			dom_event = KeyboardEvent('keyup', key=string, code=keyval_name, **key_location(keyval_name), **modifier_keys(self.get_modifier_keys(widget)))
			widget.__pressed_keys.remove(keyval)
			widget.emit('dom_event', dom_event, self.get_focus(widget))
		
		elif evtype == 'MODIFIERS':
			widget.__modifier_keys = modifiers

