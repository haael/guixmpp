#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'DisplayView',


import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib

import cairo


class DisplayView:
	def set_image(self, widget, image):
		alloc = widget.get_allocation()
		widget.__viewport_width = alloc.width
		widget.__viewport_height = alloc.height
		widget.__dpi = 96 # TODO: get dpi from gtk
		
		widget.__image = image
		GLib.idle_add(self.update, widget)
	
	def get_image(self, widget):
		try:
			return widget.__image
		except AttributeError:
			return None
	
	def get_viewport_width(self, widget):
		return widget.__viewport_width
	
	def get_viewport_height(self, widget):
		return widget.__viewport_height
	
	def get_dpi(self, widget):
		return widget.__dpi
	
	def handle_event(self, widget, event, name):
		if name != 'display': return NotImplemented
		
		if event.type == Gdk.EventType.CONFIGURE:
			widget.__viewport_width = event.width
			widget.__viewport_height = event.height
			self.update(widget)
	
	def update(self, widget):
		if hasattr(widget, '_DisplayView__surface') and widget.__surface:
			widget.__surface.finish()
			del widget.__surface
		widget.__surface = widget.draw_image(self)
		widget.queue_draw()
	
	def draw(self, widget, ctx):
		if hasattr(widget, '_DisplayView__surface') and widget.__surface:
			ctx.set_source_surface(widget.__surface)
		ctx.paint()
