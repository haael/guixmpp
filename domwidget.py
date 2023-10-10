#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'SVGWidget',


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib

from domevents import *

import cairo

from enum import Enum
from math import hypot
from itertools import zip_longest, chain
from collections import namedtuple, defaultdict



class DOMWidget(Gtk.DrawingArea):
	"Widget implementing Document Object Model."
	
	__gsignals__ = {
		'dom_event': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))
	}
	
	def __init__(self, model):
		super().__init__()
		
		self.set_can_focus(True)
		
		self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
		self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
		self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)		
		self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
		self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
		self.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
		
		self.model = model
		self.model.set_image(self, None)
		
		self.connect('draw', self.model.draw)
		self.connect('configure-event', self.model.handle_event, 'display')
		self.connect('motion-notify-event', self.model.handle_event, 'motion')
		self.connect('button-press-event', self.model.handle_event, 'button')
		self.connect('button-release-event',self.model.handle_event, 'button')
		#self.connect('clicked', self.model.handle_event, 'click')
		#self.connect('auxclicked', self.model.handle_event, 'click')
		#self.connect('dblclicked', self.model.handle_event, 'click')
		self.connect('scroll-event', self.model.handle_event, 'scroll')
		self.connect('key-press-event', self.model.handle_event, 'key')
		self.connect('key-release-event', self.model.handle_event, 'key')
	
	async def open_document(self, url):
		"Open image identified by the provided url. No image may be opened currently."
		print("open document", url)
		await self.model.open_document(self, url)
	
	def close_document(self):
		"Close current image, reverting to default state."
		self.model.close_document(self)
	
	def set_image(self, image):
		"Set current image to the document provided."
		self.model.set_image(self, image)
	
	def draw_image(self, widget, model):
		"Draw the currently opened image to a Cairo surface. Returns the rendered surface."
		
		viewport_width = model.get_viewport_width(widget)
		viewport_height = model.get_viewport_height(widget)
		
		#surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, None)
		surface = cairo.ImageSurface(cairo.Format.ARGB32, viewport_width, viewport_height)
		context = cairo.Context(surface)
		#context.set_source_rgb(1, 1, 1)
		#context.paint() # background
		
		image = model.get_image(self)
		if (image is not None) and (viewport_width > 0) and (viewport_height > 0):
			w, h = self.model.image_dimensions(self, image)
			if w / h <= viewport_width / viewport_height:
				bw = (w / h) * viewport_height
				bh = viewport_height
			else:
				bw = viewport_width
				bh = (h / w) * viewport_width
			
			model.draw_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh))
		
		#print("draw image")
		return surface
	
	def poke_image(self, px, py):
		"Simulate pointer event at widget coordinates (px, py). Returns a list of nodes under the provided point and coordinates (qx, qy) after Cairo context transformations."
		
		viewport_width = self.model.get_viewport_width(widget)
		viewport_height = self.model.get_viewport_height(widget)
		
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, (0, 0, viewport_width, viewport_height))
		context = cairo.Context(surface)
		
		image = model.get_image(self)
		if (image is not None) and (viewport_width > 0) and (viewport_height > 0):			
			w, h = self.model.image_dimensions(self, image)
			if w / h <= viewport_width / viewport_height:
				bw = (w / h) * viewport_height
				bh = viewport_height
			else:
				bw = viewport_width
				bh = (h / w) * viewport_width
			
			qx, qy = context.device_to_user(px, py)
			nop = self.model.poke_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh), px, py)
		
		else:
			qx, qy = px, py
			nop = []
		
		surface.finish()
		return nop, qx, qy


if __debug__ and __name__ == '__main__':
	import signal
	from asyncio import run, set_event_loop_policy
	from asyncio_glib import GLibEventLoopPolicy
	from aiopath import AsyncPath as Path
	
	from document import Model
	
	from format.null import NullFormat
	from format.plain import PlainFormat
	from format.xml import XMLFormat
	from format.css import CSSFormat
	from format.xforms import XFormsFormat
	from format.font import FontFormat
	
	from image.svg import SVGImage
	from image.png import PNGImage
	from image.pixbuf import PixbufImage
	
	from download.data import DataDownload
	from download.file import FileDownload
	from download.http import HTTPDownload
	
	from view.display import DisplayView
	from view.keyboard import KeyboardView
	from view.pointer import PointerView
	
	set_event_loop_policy(GLibEventLoopPolicy())
	
	model = Model.features('TestWidgetModel', DisplayView, KeyboardView, PointerView, SVGImage, PNGImage, PixbufImage, FontFormat, XFormsFormat, XMLFormat, CSSFormat, PlainFormat, NullFormat, DataDownload, FileDownload, HTTPDownload)()
	
	window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
	window.set_title('SVG test widget')
	widget = DOMWidget(model)
	window.add(widget)
	window.show_all()
	
	mainloop = GLib.MainLoop()
	window.connect('destroy', lambda window: mainloop.quit())
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	#def exception_hook(exception, y, z):
	#	sys.__excepthook__(exception, y, z)
	#	#errorbox = gtk.MessageDialog(window, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.CLOSE, str(exception))
	#	#errorbox.run()
	#	#errorbox.destroy()
	#	svgwidget.reset_after_exception()
	#
	#sys.excepthook = lambda *args: exception_hook(*args)
	
	def schedule(old_callback):
		def false_callback(*args):
			old_callback(*args)
			return False
		
		def new_callback(*args):
			GLib.idle_add(lambda: false_callback(*args))
		
		return new_callback
	
	def dom_event(widget, event):
		print(event)
		global images, image_index
		
		if event.type_ == 'warning':
			print(event)
		
		elif event.type_ == 'keyup':
			if (event.target == None) and (event.code == 'Escape'):
				schedule(widget.close_document)()
				schedule(window.close)()
			elif (event.target == None) and (event.code == 'Left') and images:
				image_index -= 1
				image_index %= len(images)
				schedule(widget.close_document)()
				schedule(run)(widget.open_document(images[image_index]))
			elif (event.target == None) and (event.code == 'Right') and images:
				image_index += 1
				image_index %= len(images)
				schedule(widget.close_document)()
				schedule(run)(widget.open_document(images[image_index]))
		
		elif event.type_ == 'opening':
			widget.main_url = event.detail
			schedule(widget.set_image)(None)
		
		elif event.type_ == 'open':
			#print("open...", widget.main_url)
			if event.detail == widget.main_url:
				schedule(widget.set_image)(event.target)
				#schedule(widget.queue_draw)()
			else:
				schedule(widget.set_image)(widget.image)
				#schedule(widget.queue_draw)()
		
		elif event.type_ == 'close':
			widget.main_url = None
			schedule(widget.set_image)(None)
		
		#else:
		#	schedule(widget.queue_draw)()
	
	widget.connect('dom_event', dom_event)
	
	images = []
	image_index = 0
	
	#async def load_images():
	#	"Display images from local directory, switch using left-right cursor key."
	#	global images, image_index, model
	#	
	#	model.font_dir = await Path('~/.cache/guixmpp-fonts').expanduser()
	#	await model.font_dir.mkdir(parents=True, exist_ok=True)
	#	
	#	async for image in (Path.cwd() / 'examples/gfx').iterdir():
	#		if image.suffix not in ('.svg', '.png', '.jpeg'): continue
	#		images.append(image.as_uri())
	#	
	#	#images.sort(key=(lambda x: f'{len(x):03d}' +  x.lower()))
	#	images.sort(key=(lambda x: x.lower()))
	#	await widget.open_document(images[image_index])
	
	async def load_images():
		"Display image from http url."
		for n in range(200):
			images.append(f'https://www.w3.org/Consortium/Offices/Presentations/SVG/{n}.svg')
		images[19] = 'https://www.w3.org/Consortium/Offices/Presentations/SVG/0.svg'
		await widget.open_document(images[image_index])
		#await widget.open_document('https://www.w3.org/Consortium/Offices/Presentations/SVG/0.svg')
	
	GLib.idle_add(lambda: run(load_images()))
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	

