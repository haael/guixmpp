#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'Renderer', 'render_to_surface', 'Rect'


import gi
if __name__ == '__main__':
	gi.require_version('Pango', '1.0')
	gi.require_version('PangoCairo', '1.0')
	gi.require_version('GdkPixbuf', '2.0')
	gi.require_version('Gdk', '4.0')

import cairo

from enum import Enum
from math import hypot
from itertools import zip_longest, chain
from collections import namedtuple, defaultdict
from asyncio import Lock, get_event_loop, get_running_loop, run, wait_for


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
	def __init__(self, file_download=False, http_download=False, cid_download=False, chrome=None, http_cache=None, http_semaphore=None, widget=None, log=None):
		self.lock = Lock()
		self.main_url = None
		
		self.file_download = file_download
		self.http_download = http_download
		self.cid_download = cid_download
		self.chrome = chrome
		self.http_cache = http_cache
		self.http_semaphore = http_semaphore
		self.widget = widget
		self.log = log
		
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
		if self.http_cache:
			cache_dir, cache_fresh_time, cache_max_time = self.http_cache
			self.model = RenderModel(chrome_dir=self.chrome, http_cache_dir=cache_dir, http_cache_fresh_time=cache_fresh_time, http_cache_max_time=cache_max_time, http_semaphore=self.http_semaphore)
		else:
			self.model = RenderModel(chrome_dir=self.chrome, http_semaphore=self.http_semaphore)
	
	async def open(self, url):
		print("open renderer")
		async with self.lock:
			print("lock grabbed")
			if self.main_url is not None:
				print("close previous document")
				await self.model.close_document(self)
			self.main_url = url
			print("open new document")
			image = await wait_for(self.model.open_document(self, url), 5)
			print("set image", image)
			self.set_image(image)
			print("set image done")
		print("open renderer done")
	
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
		callback = (lambda _reason, _param: True)
		
		viewport_width = model.get_viewport_width(self)
		viewport_height = model.get_viewport_height(self)
		
		surface = cairo.ImageSurface(cairo.Format.ARGB32, viewport_width, viewport_height)
		context = cairo.Context(surface)
		
		image = model.get_image(self)
		if (image is not None) and (viewport_width > 0) and (viewport_height > 0):
			try:
				w, h = model.image_dimensions(self, image, callback)
				
				if w <= viewport_width and h <= viewport_height:
					bw = w
					bh = h
				elif w / h <= viewport_width / viewport_height:
					bw = model.image_width_for_height(self, image, viewport_height, callback)
					bh = viewport_height
				else:
					bw = viewport_width
					bh = model.image_height_for_width(self, image, viewport_width, callback)
				
				model.draw_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh), callback)
			
			except NotImplementedError as error:
				model.emit_warning(self, f"NotImplementedError: {error}", image)
				pass # draw placeholder for non-image formats
		
		return surface
	
	def render_to_context(self, context):
		model = self.model
		callback = (lambda _reason, _param: True)
		
		viewport_width = model.get_viewport_width(self)
		viewport_height = model.get_viewport_height(self)
		
		image = model.get_image(self)
		if (image is not None) and (viewport_width > 0) and (viewport_height > 0):
			try:
				w, h = model.image_dimensions(self, image, callback)
				
				if w <= viewport_width and h <= viewport_height:
					bw = w
					bh = h
				elif w / h <= viewport_width / viewport_height:
					bw = model.image_width_for_height(self, image, viewport_height, callback)
					bh = viewport_height
				else:
					bw = viewport_width
					bh = model.image_height_for_width(self, image, viewport_width, callback)
				
				model.draw_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh), callback)
			
			except NotImplementedError as error:
				model.emit_warning(self, f"NotImplementedError: {error}", image)
				pass # draw placeholder for non-image formats
	
	def emit(self, type_, event, view):
		if self.log:
			if type_ == 'dom_event':
				if event.target == 'error':
					self.log.error(f"{type_}: {event.detail}")
				elif event.target == 'warning':
					self.log.warning(f"{type_}: {event.detail}")
				else:
					self.log.info(f"{type_}: {event.detail}")
			self.log.debug("Event: " + str(event))
		
		if self.widget:
			self.widget.emit(type_, event, view)
	
	def set_allocation(self, allocation):
		print("set_allocation")
		self.allocation = allocation
		allocation.type = Gdk.EventType.CONFIGURE
		self.model.handle_event(self, allocation, 'display')
	
	def get_allocation(self):
		print("get_allocation")
		try:
			return self.allocation
		except AttributeError:
			return Rect(0, 0, 0, 0)


async def render_to_surface(w, h, url, file_download=False, http_download=False, cid_download=False, chrome=None, http_cache=None, http_semaphore=None, widget=None, log=None):
	model = Renderer(file_download=file_download, http_download=http_download, cid_download=cid_download, chrome=chrome, http_cache=http_cache, http_semaphore=http_semaphore, widget=widget, log=log)
	await model.open(url)
	model.set_allocation(Rect(0, 0, w, h))
	try:
		s = model.render()
	finally:
		await model.close()
	return s


if __name__ == '__main__':
	from asyncio import run
	from guixmpp.mainloop import loop_init
	
	loop_init()
	
	async def main():
		DOMEvent._time = get_running_loop().time
		s = await render_to_surface(32, 32, 'file:///home/haael/Projekty/_desktop/guixmpp/examples/gfx/gradient_radial.svg', file_download=True)
		print(s)
	
	run(main())


