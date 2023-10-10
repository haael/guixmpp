#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'DisplayView',


import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

import cairo


class DisplayView:
	def set_image(self, widget, image):
		alloc = widget.get_allocation()
		widget.__viewport_width = alloc.width
		widget.__viewport_height = alloc.height
		widget.__dpi = 96 # TODO: get dpi from gtk
		
		widget.__image = image
		if image is None:
			widget.__surface = cairo.ImageSurface(cairo.Format.ARGB32, self.get_viewport_width(widget), self.get_viewport_height(widget))
		
		self.update(widget)
	
	def get_image(self, widget):
		return widget.__image
	
	def get_viewport_width(self, widget):
		return widget.__viewport_width
	
	def get_viewport_height(self, widget):
		return widget.__viewport_height
	
	def get_dpi(self, widget):
		return widget.__dpi
	
	def handle_event(self, widget, event, name):
		if name != 'display': return
		
		if event.type == Gdk.EventType.CONFIGURE:
			widget.__viewport_width = event.width
			widget.__viewport_height = event.height
			self.update(widget)
	
	def update(self, widget):
		document = self.current_document(widget)
		if document is not None:
			widget.__surface.finish()
			widget.__surface = widget.draw_image(widget, self)
			widget.queue_draw()
	
	def draw(self, widget, ctx):
		ctx.set_source_surface(widget.__surface)
		ctx.paint()

