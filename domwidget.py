#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'SVGWidget',


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GLib

import cairo

from enum import Enum
from math import hypot
from itertools import zip_longest, chain
from collections import namedtuple, defaultdict

from domevents import *

from document import Model, DocumentNotFound

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
from download.chrome import ChromeDownload

from view.display import DisplayView
from view.keyboard import KeyboardView
from view.pointer import PointerView


class DOMWidget(Gtk.DrawingArea):
	"Widget implementing Document Object Model."
	
	__gtype_name__ = 'DOMWidget'
	
	__gsignals__ = {
		'dom_event': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))
	}
	
	def __init__(self, keyboard_input=False, pointer_input=False, xforms=False, file_download=False, http_download=False, chrome=None):
		super().__init__()
		
		self.set_can_focus(True)
		
		self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
		self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
		self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)		
		self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
		self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
		self.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
		
		features = []
		if keyboard_input: features.append(KeyboardView)
		if pointer_input: features.append(PointerView)
		if xforms: features.append(XFormsFormat)
		if file_download: features.append(FileDownload)
		if http_download: features.append(HTTPDownload)
		if chrome:
			features.append(chrome)
		else:
			features.append(ChromeDownload)
		
		self.model = Model.features('<local>.DOMWidgetModel', DisplayView, SVGImage, PNGImage, PixbufImage, FontFormat, *features, XMLFormat, CSSFormat, PlainFormat, NullFormat, DataDownload)()
		self.main_url = None
		
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
		
		self.model.set_view(self)
	
	async def open_document(self, url):
		"Open image identified by the provided url. No image may be opened currently."
		await self.model.open_document(self, url)
	
	async def close_document(self):
		"Close current image, reverting to default state."
		await self.model.close_document(self)
	
	#def confirm_closed(self):
	#	self.model.confirm_closed()
	
	def set_image(self, image):
		"Set current image to the document provided."
		self.model.set_image(self, image)
	
	def get_image(self):
		self.model.get_image(self)
	
	def draw_image(self, model):
		"Draw the currently opened image to a Cairo surface. Returns the rendered surface."
		
		viewport_width = model.get_viewport_width(self)
		viewport_height = model.get_viewport_height(self)
		
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, (0, 0, viewport_width, viewport_height))
		#surface = cairo.ImageSurface(cairo.Format.ARGB32, viewport_width, viewport_height)
		context = cairo.Context(surface)
		
		image = self.model.get_image(self)
		#print("draw_image", image)
		if (image is not None) and (viewport_width > 0) and (viewport_height > 0):
			try:
				w, h = self.model.image_dimensions(self, image)
				if w / h <= viewport_width / viewport_height:
					bw = (w / h) * viewport_height
					bh = viewport_height
				else:
					bw = viewport_width
					bh = (h / w) * viewport_width
				
				model.draw_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh))
			except NotImplementedError:
				pass # draw placeholder for non-image formats
		
		#print("draw image", image)
		return surface
	
	def poke_image(self, px, py):
		"Simulate pointer event at widget coordinates (px, py). Returns a list of nodes under the provided point and coordinates (qx, qy) after Cairo context transformations."
		
		viewport_width = self.model.get_viewport_width(widget)
		viewport_height = self.model.get_viewport_height(widget)
		
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, (0, 0, viewport_width, viewport_height))
		context = cairo.Context(surface)
		
		qx, qy = px, py
		nop = []
		
		image = self.model.get_image(self)
		if (image is not None) and (viewport_width > 0) and (viewport_height > 0):			
			try:
				w, h = self.model.image_dimensions(self, image)
				if w / h <= viewport_width / viewport_height:
					bw = (w / h) * viewport_height
					bh = viewport_height
				else:
					bw = viewport_width
					bh = (h / w) * viewport_width
				
				qx, qy = context.device_to_user(px, py)
				nop = self.model.poke_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh), px, py)
			except NotImplementedError:
				pass
		
		surface.finish()
		return nop, qx, qy


if __debug__ and __name__ == '__main__':
	import signal
	from asyncio import run, Condition
	from aiopath import AsyncPath as Path
	
	from mainloop import *
	
	loop_init()
	
	window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
	window.set_title('SVG test widget')
	widget = DOMWidget(keyboard_input=True, pointer_input=True, xforms=True, file_download=True, http_download=True)
	window.add(widget)
	
	window.connect('destroy', lambda window: loop_quit())
	signal.signal(signal.SIGTERM, lambda signum, frame: loop_quit())
	
	doc_cond = Condition()
	
	@asynchandler
	async def dom_event(widget, event):
		global images, image_index
		
		if event.type_ == 'warning':
			print(event)
		
		if event.type_ == 'keyup':
			if (event.target == None) and (event.code == 'Escape'):
				async with doc_cond:
					await widget.close_document()
					await doc_cond.wait_for(lambda: widget.get_image() is None)
					window.close()
			elif (event.target == None) and (event.code == 'Left') and images:
				async with doc_cond:
					image_index -= 1
					image_index %= len(images)
					await widget.close_document()
					await doc_cond.wait_for(lambda: widget.get_image() is None)
					await widget.open_document(images[image_index])
			elif (event.target == None) and (event.code == 'Right') and images:
				async with doc_cond:
					image_index += 1
					image_index %= len(images)
					await widget.close_document()
					await doc_cond.wait_for(lambda: widget.get_image() is None)
					await widget.open_document(images[image_index])
		
		elif event.type_ == 'opening':
			async with doc_cond:
				widget.main_url = event.detail
				doc_cond.notify_all()
		
		elif event.type_ == 'open':
			async with doc_cond:
				await doc_cond.wait_for(lambda: widget.main_url is not None)
				try:
					if event.detail == widget.main_url:
						widget.set_image(event.target)
					else:
						widget.set_image(widget.image)
				except DocumentNotFound:
					pass
		
		elif event.type_ == 'closing':
			async with doc_cond:
				widget.main_url = None
				doc_cond.notify_all()
		
		elif event.type_ == 'close':
			async with doc_cond:
				await doc_cond.wait_for(lambda: widget.main_url is None)
				widget.set_image(None)
				doc_cond.notify_all()
	
	widget.connect('dom_event', dom_event)
	
	images = []
	image_index = 0
	
	#'''
	async def main():
		"Display images from local directory, switch using left-right cursor key."
		
		global images, image_index, model
		
		widget.model.font_dir = await Path('~/.cache/guixmpp-fonts').expanduser()
		await widget.model.font_dir.mkdir(parents=True, exist_ok=True)
		
		async for image in (Path.cwd() / 'examples/gfx').iterdir():
			if image.suffix not in ('.txt', '.css', '.xml', '.svg_'):
				images.append(image.as_uri())
		
		#images.sort(key=(lambda x: f'{len(x):03d}' + x.lower()))
		images.sort(key=(lambda x: x.lower()))
		await widget.open_document(images[image_index])
		
		window.show_all()
		await loop_run()
		window.hide()
	#'''
	
	'''
	async def main():
		"Display image from http url."
		for n in range(219):
			images.append(f'https://www.w3.org/Consortium/Offices/Presentations/SVG/{n}.svg')
		await widget.open_document(images[image_index])
		window.show_all()
		await loop_run()
		window.hide()
	#'''
	
	run(main())
