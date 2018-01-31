#!/usr/bin/python3
#-*- coding:utf-8 -*-

from __future__ import unicode_literals


import sys
import signal
import traceback

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import GObject as gobject
from gi.repository import GLib as glib
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GdkPixbuf

from math import pi as PI, sin, cos

import base64
import binascii
import hashlib

import cairo

#import sleekxmpp


def pseudo_random(seed, n):
	m = hashlib.sha256()
	m.update(bytes([max(n >> (8 * i), 0) % 256 for i in range(8)]))
	m.update(seed)
	return int.from_bytes(m.digest()[:8], byteorder='big')


def fractal(seed, ctx, level=0, subseed=0):
	
	if level >= 3: return
	
	ctx.arc(0, 0, 1, 0, 2 * PI)
	ctx.clip()
	
	color1 = (pseudo_random(seed, 0) % 256) / 256, (pseudo_random(seed, 1) % 256) / 256, (pseudo_random(seed, 2) % 256) / 256
	color2 = (pseudo_random(seed, 3) % 256) / 256, (pseudo_random(seed, 4) % 256) / 256, (pseudo_random(seed, 5) % 256) / 256
	color3 = (pseudo_random(seed, 6) % 256) / 256, (pseudo_random(seed, 7) % 256) / 256, (pseudo_random(seed, 8) % 256) / 256
	color4 = (pseudo_random(seed, 9) % 256) / 256, (pseudo_random(seed, 10) % 256) / 256, (pseudo_random(seed, 11) % 256) / 256
	color5 = (pseudo_random(seed, 31) % 256) / 256, (pseudo_random(seed, 32) % 256) / 256, (pseudo_random(seed, 33) % 256) / 256

	ctx.set_line_cap(cairo.LINE_CAP_ROUND)
	#ctx.set_source_rgba(0, 0, 0, 0.25)
	#ctx.arc(0, 0, 1, 0, 2 * PI)
	#ctx.fill()
	
	for i in range(pseudo_random(seed, subseed + 1000 * level + 12) % 5 + 5):
		length = 0.25 * (pseudo_random(seed, subseed + 1000 * level + 100 * i + 13) % 1024 / 1024) + 0.25
		angle = (pseudo_random(seed, subseed + 1000 * level + 100 * i + 14) % 360 / 360) * 2 * PI
		width1 = 1 * (pseudo_random(seed, subseed + 1000 * level + 100 * i + 15) % 10 / 1000) + 0.01
		width2 = 1 * (pseudo_random(seed, subseed + 1000 * level + 100 * i + 16) % 10 / 1000) + width1
		
		sin_angle = sin(angle)
		cos_angle = cos(angle)
		x = length * sin_angle
		y = length * cos_angle

		shapetype = pseudo_random(seed, subseed + 1000 * level + 100 * i + 34) % 10
		
		if shapetype < 7:
			ctx.move_to(0, 0)
			ctx.line_to(x, y)
			ctx.set_line_width(width2)
			ctx.set_source_rgba(*color1, 0.5)
			ctx.stroke()
			
			ctx.move_to(0, 0)
			ctx.line_to(x, y)
			ctx.set_line_width(width1)
			ctx.set_source_rgb(*color2)
			ctx.stroke()
		else:
			distance1 = (pseudo_random(seed, subseed + 1000 * level + 100 * i + 35) % 1024 / 1024) * length
			displace1 = 0.5 * (pseudo_random(seed, subseed + 1000 * level + 100 * i + 36) % 20 / 20)
			distance2 = (pseudo_random(seed, subseed + 1000 * level + 100 * i + 37) % 1024 / 1024) * length
			displace2 = 0.5 * (pseudo_random(seed, subseed + 1000 * level + 100 * i + 38) % 20 / 20)

			x1 = distance1 * sin_angle + displace1 * cos_angle
			y1 = distance1 * cos_angle - displace1 * sin_angle
			x2 = distance2 * sin_angle + displace2 * cos_angle
			y2 = distance2 * cos_angle - displace2 * sin_angle
			
			ctx.move_to(0, 0)
			ctx.curve_to(x1, y1, x2, y2, x, y)
			ctx.set_source_rgb(*color2)
			ctx.stroke()
			
		
		for j in range(pseudo_random(seed, subseed + 1000 * level + 100 * i + 17) % 20):
			distance = (pseudo_random(seed, subseed + 1000 * level + 100 * i + 17 + j) % 1024 / 1024) * length
			displace = 0.1 * (pseudo_random(seed, subseed + 1000 * level + 100 * i + 18 + j) % 20 / 20)
			spotsize = 0.005 * (pseudo_random(seed, subseed + 1000 * level + 100 * i + 19 + j) % 10 + 5)
			shapetype = pseudo_random(seed, subseed + 1000 * level + 100 * i + 20 + j) % 4
			
			x = distance * sin_angle + displace * cos_angle
			y = distance * cos_angle - displace * sin_angle
			
			if shapetype == 0:
				gradient = cairo.RadialGradient(x, y, 0, x, y, spotsize)
				gradient.add_color_stop_rgba(0, *color3, 1)
				gradient.add_color_stop_rgba(1, *color4, 0)
				ctx.set_source(gradient)
				ctx.arc(x, y, spotsize, 0, 2 * PI)
				ctx.fill()
				del gradient
			elif shapetype == 1:
				ctx.set_source_rgb(*color4)
				ctx.save()
				ctx.rotate(angle)
				ctx.rectangle(x - spotsize / 2, y - spotsize / 2, spotsize / 2, spotsize / 2)
				ctx.fill()
				ctx.restore()
			elif shapetype == 2:
				ctx.set_source_rgb(*color5)
				ctx.save()
				ctx.rotate(angle + PI / 4)
				ctx.rectangle(x - spotsize / 4, y - spotsize / 4, spotsize / 4, spotsize / 4)
				ctx.fill()
				ctx.restore()
			elif shapetype == 3:
				ctx.set_source_rgb(*color3)
				ctx.arc(x + spotsize / 4, y, spotsize / 4, 0, 2 * PI)
				ctx.arc(x - spotsize / 4, y, spotsize / 4, 0, 2 * PI)
				ctx.arc(x, y + spotsize / 4, spotsize / 4, 0, 2 * PI)
				ctx.arc(x, y - spotsize / 4, spotsize / 4, 0, 2 * PI)
				ctx.fill()
				ctx.set_source_rgb(*color1)
				ctx.arc(x, y, spotsize / 4, 0, 2 * PI)
				ctx.fill()
		
		ctx.save()
		ctx.translate(length * sin_angle, length * cos_angle)
		ctx.rotate(angle)
		ctx.scale(0.5, 0.5)
		
		fractal(seed, ctx, level=level + 1, subseed=pseudo_random(seed, subseed + 1000 * level + 100 * i + 30))
		
		ctx.restore()




if __name__ == '__main__':
	glib.threads_init()
	
	css = gtk.CssProvider()
	css.load_from_path('style.css')
	gtk.StyleContext().add_provider_for_screen(gdk.Screen.get_default(), css, gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	window = gtk.Window()
	canvas = gtk.DrawingArea()
	seed = binascii.unhexlify('693570293735980ab3984724a0cc')
	def draw(widget, context):
		allocation = widget.get_allocation()
		context.translate(allocation.width / 2, allocation.height / 2)
		radius = min(allocation.width / 2, allocation.height / 2)
		context.scale(radius, radius)
		fractal(seed, context)
	canvas.connect('draw', draw)
	window.add(canvas)
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	window.connect('destroy', lambda widget: mainloop.quit())	
	window.show_all()
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()


