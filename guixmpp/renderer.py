#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'Renderer', 'render_to_surface'


#import gi
#gi.require_version('Gtk', '3.0')
#gi.require_version('Gio', '2.0')
#from gi.repository import Gtk, Gdk, GObject, GLib, Gio

import cairo

from enum import Enum
from math import hypot
from itertools import zip_longest, chain
from collections import namedtuple, defaultdict
from asyncio import Lock, get_event_loop, get_running_loop, run


if __name__ == '__main__':
	from guixmpp.domevents import *
	DOMEvent = Event
	
	from guixmpp.document import Model, DocumentNotFound
	
	from guixmpp.format.null import NullFormat
	from guixmpp.format.plain import PlainFormat
	from guixmpp.format.xml import XMLFormat
	from guixmpp.format.css import CSSFormat
	from guixmpp.format.font import FontFormat
	
	from guixmpp.render.svg import SVGRender
	from guixmpp.render.png import PNGRender
	from guixmpp.render.webp import WEBPRender
	from guixmpp.render.pixbuf import PixbufRender
	from guixmpp.render.html import HTMLRender
	#from guixmpp.format.xforms import XFormsFormat
	
	from guixmpp.download.data import DataDownload
	from guixmpp.download.file import FileDownload
	from guixmpp.download.http import HTTPDownload
	from guixmpp.download.cid import CIDDownload
	from guixmpp.download.chrome import ChromeDownload
	from guixmpp.download.resource import ResourceDownload
	
	from guixmpp.view.display import DisplayView
	from guixmpp.view.keyboard import KeyboardView
	from guixmpp.view.pointer import PointerView

else:
	from .domevents import *
	DOMEvent = Event
	
	from .document import Model, DocumentNotFound
	
	from .format.null import NullFormat
	from .format.plain import PlainFormat
	from .format.xml import XMLFormat
	from .format.css import CSSFormat
	from .format.font import FontFormat

	from .render.svg import SVGRender
	from .render.png import PNGRender
	from .render.webp import WEBPRender
	from .render.pixbuf import PixbufRender
	from .render.html import HTMLRender
	#from .format.xforms import XFormsFormat

	from .download.data import DataDownload
	from .download.file import FileDownload
	from .download.http import HTTPDownload
	from .download.cid import CIDDownload
	from .download.chrome import ChromeDownload
	from .download.resource import ResourceDownload
	
	from .view.display import DisplayView
	from .view.keyboard import KeyboardView
	from .view.pointer import PointerView


class Rect:
	def __init__(self, x, y, w, h):
		self.x = x
		self.y = y
		self.width = w
		self.height = h


class Renderer:		
	def __init__(self, file_download=False, http_download=False, cid_download=False, chrome=None):
		self.lock = Lock()
		self.main_url = None
		
		self.file_download = file_download
		self.http_download = http_download
		self.cid_download = cid_download
		self.chrome = chrome
		
		self.configure_model()
	
	def configure_model(self):
		if hasattr(self, 'model'):
			for conn in self.connections:
				self.disconnect(conn)
			del self.model, self.connections
		
		features = []
		cc = []
		if self.file_download:
			features.append(FileDownload)
			cc.append('F')
		if self.http_download:
			features.append(HTTPDownload)
			cc.append('H')
		if self.cid_download:
			features.append(CIDDownload)
			cc.append('C')
		
		if cc:
			cc.insert(0, '_')
		else:
			cc.append('_X')
		
		RenderModel = Model.features('<local>.RenderModel' + ''.join(cc), DisplayView, SVGRender, PNGRender, WEBPRender, PixbufRender, HTMLRender, FontFormat, *features, ChromeDownload, ResourceDownload, XMLFormat, CSSFormat, PlainFormat, NullFormat, DataDownload)
		self.model = RenderModel(chrome_dir=self.chrome)
	
	async def open(self, w, h, url):
		self.allocation = Rect(0, 0, w, h)
		
		async with self.lock:
			if self.main_url is not None:
				await self.model.close_document(self)
			self.main_url = url
			image = await self.model.open_document(self, url)
			self.set_image(image)
	
	async def close(self):
		async with self.lock:
			if self.main_url is not None:
				self.main_url = None
				await self.model.close_document(self)
				self.set_image(None)
	
	def set_image(self, image):
		"Directly set image to display (document returned by `model.create_document`). None to unset."
		
		self.model.set_image(self, image)
	
	def draw_image(self, image):
		pass # ignored
	
	def queue_draw(self):
		pass # ignored
	
	def render(self):
		model = self.model
		
		viewport_width = model.get_viewport_width(self)
		viewport_height = model.get_viewport_height(self)
		
		surface = cairo.ImageSurface(cairo.Format.ARGB32, viewport_width, viewport_height)
		context = cairo.Context(surface)
		
		image = model.get_image(self)
		if (image is not None) and (viewport_width > 0) and (viewport_height > 0):
			try:
				w, h = model.image_dimensions(self, image)
				
				if w <= viewport_width and h <= viewport_height:
					bw = w
					bh = h
				elif w / h <= viewport_width / viewport_height:
					bw = model.image_width_for_height(self, image, viewport_height)
					bh = viewport_height
				else:
					bw = viewport_width
					bh = model.image_height_for_width(self, image, viewport_width)
				
				model.draw_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh))
			
			except NotImplementedError as error:
				model.emit_warning(self, f"NotImplementedError: {error}", image)
				pass # draw placeholder for non-image formats
		
		return surface
	
	def emit(self, type_, event, view):
		print(type_, event)
	
	def get_allocation(self):
		return self.allocation


async def render_to_surface(w, h, url, file_download=False, http_download=False, cid_download=False, chrome=None):
	r = Renderer(file_download=file_download, http_download=http_download, cid_download=cid_download, chrome=chrome)
	await r.open(w, h, url)
	try:
		s = r.render()
	finally:
		await r.close()
	return s


if __name__ == '__main__':
	from asyncio import run
	
	async def main():
		DOMEvent._time = get_running_loop().time
		s = await render(32, 32, 'file:///home/haael/Projekty/guixmpp/examples/gfx/gradient_radial.svg', file_download=True)
		print(s)
	
	run(main())


