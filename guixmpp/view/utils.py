#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'modifier_keys', 'pressed_mouse_buttons_mask', 'pressed_mouse_button', 'pointer_position'


import gi
#gi.require_version('Gdk', '3.0')
from gi.repository import Gdk


def modifier(attr):
	try:
		return getattr(Gdk.ModifierType, attr)
	except AttributeError:
		return 0


def modifier_keys(modifiers):
	return {
		'shiftKey': bool(modifiers & (modifier('SHIFT_MASK') | modifier('LOCK_MASK'))),
		'ctrlKey': bool(modifiers & modifier('CONTROL_MASK')),
		'altKey': bool(modifiers & (modifier('ALT_MASK') | modifier('MOD1_MASK') | modifier('MOD5_MASK'))),
		'metaKey': bool(modifiers & (modifier('META_MASK') | modifier('SUPER_MASK') | modifier('HYPER_MASK') | modifier('MOD4_MASK')))
	}


def pressed_mouse_buttons_mask(buttons):
	mask = 0
	for b in buttons:
		mask |= 1 << b
	return {'buttons': mask}


def pressed_mouse_button(event):
	active_button = 0
	if event.button == Gdk.BUTTON_PRIMARY:
		active_button = 0
	elif event.button == Gdk.BUTTON_SECONDARY:
		active_button = 2
	elif event.button == Gdk.BUTTON_MIDDLE:
		active_button = 1
	return active_button


def pointer_position(event, qx, qy):
	if isinstance(event, tuple):
		return {
			'clientX': qx,
			'clientY': qy,
			'screenX': qx, #TODO
			'screenY': qy #TODO
		}
	else:
		return {
			'clientX': qx,
			'clientY': qy,
			'screenX': event.x_root,
			'screenY': event.y_root
		}

