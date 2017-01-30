#!/usr/bin/python3
#-*- coding: utf-8 -*-

from __future__ import unicode_literals


from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import GLib as glib

import cairo
import math

from lxml import etree



def draw_path





root = etree.parse('SVG_logo.svg')

class namespace:
	svg = 'http://www.w3.org/2000/svg'
	xlink = 'http://www.w3.org/1999/xlink'


def parse_size(src, size):
	if src is None:
		return None
	
	try:
		return float(src)
	except ValueError:
		if src[-1:] == '%':
			return float(src[:-1]) / 100 * size
		else:
			raise

def parse_color(src, default):
	if src == 'currentColor':
		return default
	elif len(src) == 7 and src[0] == '#':
		r = int(src[1:3], 16) / 255
		g = int(src[3:5], 16) / 255
		b = int(src[5:7], 16) / 255
		return 1, r, g, b
	elif len(src) == 9 and src[0] == '#':
		a = int(src[1:3], 16) / 255
		r = int(src[3:5], 16) / 255
		g = int(src[5:7], 16) / 255
		b = int(src[7:9], 16) / 255
		return a, r, g, b
	elif src == 'transparent':
		return 0, 0, 0, 0


#presentation_attributes = 
#def parse_presentation_attributes(src, dst):
#	for key in presentation_attributes:
#		if key in src:


default_attrs = {
	'color':'transparent', 'stroke':'none', 'fill':'black'
	
	#'cursor'
	#'direction', 'display', 'enable-background', 'fill', 'fill-opacity', 'fill-rule', 'filter', 'flood-color'
	#'flood-opacity',  'image-rendering', 'lighting-color', 'marker-end'
	#'marker-mid', 'marker-start', 'mask', 'opacity', 'overflow', 'pointer-events', 'shape-rendering', 'stop-color', 'stop-opacity', 'stroke'
	#'stroke-dasharray', 'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-opacity', 'stroke-width'
	#'visibility'
	
	#alignment_baseline = element.get('alignment-baseline') or attrs['alignment-baseline']
	#baseline-shift = element.get('baseline-shift') or attrs['baseline-shift']
	#'font-family', 'font-size', 'font-size-adjust', 'font-stretch', 'font-style', 'font-variant', 'font-weight'
	#'glyph-orientation-horizontal', 'glyph-orientation-vertical'
	#'text-anchor', 'text-decoration', 'text-rendering', 'unicode-bidi', 'word-spacing', 'writing-mode'
	#'kerning', 'letter-spacing', 'dominant-baseline'
	
	#'color-interpolation', 'color-interpolation-filters', 'color-profile', 'color-rendering'
	#clip = value('clip')
	#clip_path = value('clip-path')
	#clip_rule = value('clip-rule')
}


def graphics_element(context, element, parent_attrs):
	#'cursor'
	#'direction', 'display', 'enable-background', 'fill-opacity', 'fill-rule', 'filter', 'flood-color'
	#'flood-opacity',  'image-rendering', 'lighting-color', 'marker-end'
	#'marker-mid', 'marker-start', 'mask', 'opacity', 'overflow', 'pointer-events', 'shape-rendering', 'stop-color', 'stop-opacity', 'stroke'
	#'stroke-dasharray', 'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-opacity', 'stroke-width'
	#'visibility'
	
	#alignment_baseline = element.get('alignment-baseline') or attrs['alignment-baseline']
	#baseline-shift = element.get('baseline-shift') or attrs['baseline-shift']
	#'font-family', 'font-size', 'font-size-adjust', 'font-stretch', 'font-style', 'font-variant', 'font-weight'
	#'glyph-orientation-horizontal', 'glyph-orientation-vertical'
	#'text-anchor', 'text-decoration', 'text-rendering', 'unicode-bidi', 'word-spacing', 'writing-mode'
	#'kerning', 'letter-spacing', 'dominant-baseline'
	
	#'color-interpolation', 'color-interpolation-filters', 'color-profile', 'color-rendering'
	#clip = value('clip')
	#clip_path = value('clip-path')
	#clip_rule = value('clip-rule')
	
	def value(name, default='inherit'):
		v = element.get(name) or default
		if v == 'inherit':
			v = parent_attrs[name]
		return v
	
	color = parse_color(value('color'))
	fill = parse_color(value('fill', 'none'), color)
	stroke = parse_color(value('stroke', 'none'), color)
	
	if fill


def svg(element, context, attrs):
	if hasattr(element, 'getroot'):
		svg(element.getroot(), context, **attrs)
	elif element.tag == '{%s}svg' % namespace.svg:
		w = parse_size(element.get('width'), width) or width
		h = parse_size(element.get('height'), height) or height
		
		m = context.get_matrix()
		viewBox = element.get('viewBox')
		if viewBox:
			vbsrc = viewBox.split(' ')
			vbx = parse_size(vbsrc[0], width)
			vby = parse_size(vbsrc[1], height)
			vbw = parse_size(vbsrc[2], width)
			vbh = parse_size(vbsrc[3], height)
			context.translate(vbx, vby)
			context.scale(w / vbw, h / vbh)
		for child in element:
			svg(child, context, width=w, height=h, **attrs)
		context.set_matrix(m)





def svg(element, context, width, height):
	if hasattr(element, 'getroot'):
		svg(element.getroot(), context, width, height)
	elif not hasattr(element, 'tag'):
		for child in element:
			svg(child, context, width, height)
	elif element.tag == '{%s}svg' % namespace.svg:
		w = parse_size(element.get('width'), width) or width
		h = parse_size(element.get('height'), height) or height
		context.scale(width / w, height / h)
		for child in element:
			svg(child, context, width, height)
	elif element.tag == '{%s}g' % namespace.svg:
		for child in element:
			svg(child, context, width, height)
	elif element.tag == '{%s}circle' % namespace.svg:
		cx = parse_size(element.get('cx'), width)
		cy = parse_size(element.get('cy'), height)
		r = parse_size(element.get('r'), None)
		
		context.arc(cx, cy, r, 0, 2 * math.pi)
		
		stroke_width = parse_size(element.get('stroke-width'), None)
		if stroke_width > 0:
			context.set_line_width(stroke_width)
		
		#context.set_source_rgb(0, 0, 0)

			#m = context.get_matrix()
			context.identity_matrix()
			context.stroke()
			#context.set_matrix(m)
		
	elif element.tag == '{%s}rect' % namespace.svg:
		x = parse_size(element.get('x'), width) or 0
		y = parse_size(element.get('y'), height) or 0
		w = parse_size(element.get('width'), width)
		h = parse_size(element.get('height'), height)
		rx = parse_size(element.get('rx'), width) or 0
		ry = parse_size(element.get('ry'), height) or 0
		
		if rx != 0 or ry != 0:
			degrees = math.pi / 180.0
			
			m = context.get_matrix()
			
			context.translate(x + w - rx, y + ry)
			context.scale(rx, ry)
			context.arc(0, 0, 1, -90 * degrees, 0 * degrees)
			context.set_matrix(m)
			
			context.translate(x + w - rx, y + h - ry)
			context.scale(rx, ry)
			context.arc(0, 0, 1, 0 * degrees, 90 * degrees)
			context.set_matrix(m)
			
			context.translate(x + rx, y + h - ry)
			context.scale(rx, ry)
			context.arc(0, 0, 1, 90 * degrees, 180 * degrees)
			context.set_matrix(m)
			
			context.translate(x + rx, y + ry)
			context.scale(rx, ry)
			context.arc(0, 0, 1, 180 * degrees, 270 * degrees)
			context.set_matrix(m)
			
			context.close_path()
		else:
			context.rectangle(x, y, w, h)
		
		m = context.get_matrix()
		context.identity_matrix()
		
		stroke_width = parse_size(element.get('stroke-width'), None) or 0
		if stroke_width > 0:
			context.set_line_width(stroke_width)
		
		#context.set_source_rgb(0, 0, 0)
		context.stroke_preserve()
		
		context.set_source_rgb(*parse_color(element.get('fill')))
		context.fill()
		
		context.set_matrix(m)
	elif element.tag == '{%s}title' % namespace.svg: # TODO: title
		pass
	elif element.tag == '{%s}a' % namespace.svg: # TODO: clickability
		for child in element:
			svg(child, context, width, height)
	else:
		print(element)
	





def draw(widget, context):
	rect = widget.get_allocation()
	x = rect.x + rect.width / 2
	y = rect.y + rect.height / 2
	svg(root, context, rect.width, rect.height)


if __name__ == '__main__':
	import signal
	
	glib.threads_init()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	window = gtk.Window(gtk.WindowType.TOPLEVEL)
	window.connect("destroy", lambda window: mainloop.quit())
	canvas = gtk.DrawingArea()
	canvas.connect("draw", lambda canvas, context: draw(canvas, context))
	window.add(canvas)
	window.show_all()
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	







