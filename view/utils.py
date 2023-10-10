#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'modifier_keys', 'pressed_mouse_buttons_mask', 'pressed_mouse_button', 'pointer_position'


import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk


def modifier_keys(event):
	return {
		'shiftKey': bool(event.state & Gdk.ModifierType.SHIFT_MASK),
		'ctrlKey': bool(event.state & Gdk.ModifierType.CONTROL_MASK),
		'altKey': bool(event.state & (Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.MOD5_MASK)),
		'metaKey': bool(event.state & (Gdk.ModifierType.META_MASK | Gdk.ModifierType.SUPER_MASK | Gdk.ModifierType.MOD4_MASK))
	}


def pressed_mouse_buttons_mask(event):
	active_buttons = 0
	if event.state & Gdk.ModifierType.BUTTON1_MASK:
		active_buttons |= 1
	if event.state & Gdk.ModifierType.BUTTON3_MASK:
		active_buttons |= 2
	if event.state & Gdk.ModifierType.BUTTON2_MASK:
		active_buttons |= 4
	return {'buttons': active_buttons}


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
	return {
		'clientX': qx,
		'clientY': qy,
		'screenX': event.x_root,
		'screenY': event.y_root
	}

