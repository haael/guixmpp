#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'DisplayView',


import gi
#gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import cairo


class DisplayView:
	def set_image(self, widget, image):
		widget.__image = image
		GLib.idle_add(self.update, widget)
	
	def get_image(self, widget):
		try:
			return widget.__image
		except AttributeError:
			return None
	
	def get_viewport_width(self, widget):
		try:
			return widget.__viewport_width
		except AttributeError:
			return 0
	
	def get_viewport_height(self, widget):
		try:
			return widget.__viewport_height
		except AttributeError:
			return 0
	
	def get_dpi(self, widget):
		try:
			return widget.__dpi
		except AttributeError:
			return 96 # TODO: get dpi from gtk
	
	def handle_event(self, widget, params, evtype, name):
		if name != 'display': return NotImplemented
		
		if evtype == 'CONFIGURE_EVENT':
			try:
				width = params.width
				height = params.height
			except AttributeError:
				width, height = params
			
			try:
				if self.get_viewport_width(widget) == width and self.get_viewport_height(widget) == height:
					return
			except AttributeError:
				pass
			widget.__viewport_width = width
			widget.__viewport_height = height
			self.update(widget)
	
	def update(self, widget):
		if Gtk.get_major_version() < 4:
			try:
				if widget.__surface:
					widget.__surface.finish()
					del widget.__surface
			except AttributeError:
				pass
			
			widget.__surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, (0, 0, widget.get_viewport_width(self), widget.get_viewport_height(self)))
			#widget.__surface = cairo.ImageSurface(cairo.Content.COLOR_ALPHA, (0, 0, widget.get_viewport_width(self), widget.get_viewport_height(self)))
			widget.draw_image(self, cairo.Context(widget.__surface))
		widget.queue_draw()
		return False
	
	def draw_gtk3(self, widget, ctx):
		"Drawing in Gtk3 is split between configure event, rendering to an offscreen surface and then painting the requested area."
		try:
			if widget.__surface:
				ctx.set_source_surface(widget.__surface)
		except AttributeError:
			pass
		ctx.paint()
	
	def draw_gtk4(self, widget, ctx, viewport_width, viewport_height):
		"Drawing in Gtk4 means simply rendering to the provided context with the given window dimensions."
		widget.__viewport_width = viewport_width
		widget.__viewport_height = viewport_height
		widget.draw_image(self, ctx)

