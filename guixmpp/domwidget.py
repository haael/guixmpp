#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'DOMWidget',


import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Gdk, GObject, GLib, Gio

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


try: # avoid defining DOMWidget twice
	if __name__ == '__main__':
		import guixmpp
		DOMWidget = guixmpp.DOMWidget
	else:
		DOMWidget

except NameError:

	class DOMWidget(Gtk.DrawingArea):
		"Widget implementing Document Object Model."
		
		__gtype_name__ = 'DOMWidget'
		
		__gsignals__ = {
			'dom_event': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))
		}
		
		__gproperties__ = {
			'keyboard_input' : (GObject.TYPE_BOOLEAN, "Keyboard input", "Whether the widget accepts keyboard input.", False, GObject.ParamFlags.READWRITE),
			'pointer_input' : (GObject.TYPE_BOOLEAN, "Pointer input", "Whether the widget accepts pointer input.", False, GObject.ParamFlags.READWRITE),
			'file_download' : (GObject.TYPE_BOOLEAN, "File download", "Whether the widget supports `file:` scheme granting access to local filesystem.", False, GObject.ParamFlags.READWRITE),
			'http_download' : (GObject.TYPE_BOOLEAN, "HTTP download", "Whether the widget supports `http(s):` scheme granting access to network.", False, GObject.ParamFlags.READWRITE),
			'cid_download' : (GObject.TYPE_BOOLEAN, "CID download", "Whether the widget supports `cid:` scheme granting access to XMPP network.", False, GObject.ParamFlags.READWRITE),
			'auto_show' : (GObject.TYPE_BOOLEAN, "Auto show", "Whether the loaded image should be shown automatically.", True, GObject.ParamFlags.READWRITE),
			'url' : (GObject.TYPE_STRING, "URL", "URL to load; the right scheme must be supported.", None, GObject.ParamFlags.READWRITE),
			'file' : (GObject.TYPE_STRING, "File", "File to load; works even if `file:` scheme is disabled.", None, GObject.ParamFlags.READWRITE)
		}
		
		def __init__(self, file_=None, url=None, keyboard_input=False, pointer_input=False, file_download=False, http_download=False, cid_download=False, chrome=None, auto_show=True):
			super().__init__()
			
			self.set_can_focus(True)
			self.lock = Lock()
			self.main_url = None
			
			self.prop_file = file_
			self.prop_url = url
			
			self.keyboard_input = keyboard_input
			self.pointer_input = pointer_input
			self.file_download = file_download
			self.http_download = http_download
			self.cid_download = cid_download
			self.chrome = chrome
			self.auto_show = auto_show
			
			self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
			self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
			self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)		
			self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
			self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
			self.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
			
			self.configure_model()
		
		def configure_model(self):
			if hasattr(self, 'model'):
				for conn in self.connections:
					self.disconnect(conn)
				del self.model, self.connections
			
			features = []
			cc = []
			if self.keyboard_input:
				features.append(KeyboardView)
				cc.append('K')
			if self.pointer_input:
				features.append(PointerView)
				cc.append('P')
			if self.file_download:
				features.append(FileDownload)
				cc.append('F')
			if self.http_download:
				features.append(HTTPDownload)
				cc.append('H')
			if self.cid_download:
				features.append(CIDDownload)
				cc.append('C')
			#if self.chrome:
			#	features.append(ChromeDownload)
			#	cc.append('C')
			
			if cc:
				cc.insert(0, '_')
			else:
				cc.append('_X')
			
			DOMWidgetModel = Model.features('<local>.DOMWidgetModel' + ''.join(cc), DisplayView, SVGRender, PNGRender, WEBPRender, PixbufRender, HTMLRender, FontFormat, *features, ChromeDownload, ResourceDownload, XMLFormat, CSSFormat, PlainFormat, NullFormat, DataDownload)
			self.model = DOMWidgetModel(chrome_dir=self.chrome)
			
			self.connections = []
			self.connections.append(self.connect('draw', self.model.draw))
			self.connections.append(self.connect('configure-event', self.model.handle_event, 'display'))
			self.connections.append(self.connect('motion-notify-event', self.model.handle_event, 'motion'))
			self.connections.append(self.connect('button-press-event', self.model.handle_event, 'button'))
			self.connections.append(self.connect('button-release-event', self.model.handle_event, 'button'))
			#self.connections.append(self.connect('clicked', self.model.handle_event, 'click'))
			#self.connections.append(self.connect('auxclicked', self.model.handle_event, 'click'))
			#self.connections.append(self.connect('dblclicked', self.model.handle_event, 'click'))
			self.connections.append(self.connect('scroll-event', self.model.handle_event, 'scroll'))
			self.connections.append(self.connect('key-press-event', self.model.handle_event, 'key'))
			self.connections.append(self.connect('key-release-event', self.model.handle_event, 'key'))
		
		def do_get_property(self, spec):
			name = spec.name.replace('-', '_')
			
			if name == 'file':
				return self.prop_file
			elif name == 'url':
				return self.prop_url
			elif name == 'auto_show':
				return self.auto_show
			else:
				return getattr(self, name)
		
		def do_set_property(self, spec, value):
			name = spec.name.replace('-', '_')
			
			if name == 'file':
				self.prop_file = value
			elif name == 'url':
				self.prop_url = value
			elif name == 'auto_show':
				self.auto_show = value
			else:
				setattr(self, name, value)
				self.configure_model()
			
			if self.prop_url:
				coro = self.open(self.prop_url)
			elif self.prop_file:
				coro = self.open('') # opening empty url will use 'file' property fallback
			else:
				return
			
			try:
				loop = get_event_loop()
			except RuntimeError:
				loop = None
			
			async def work():
				DOMEvent._time = get_running_loop().time
				await coro
			
			if not loop:
				run(work())
			elif not loop.is_running():
				loop.run_until_complete(work())
			else:
				loop.create_task(work())
		
		async def open(self, url):
			"Open document identified by the provided url."
			
			async with self.lock:
				if self.main_url is not None:
					await self.model.close_document(self)
				self.main_url = url
				image = await self.model.open_document(self, url)
				if self.auto_show:
					self.set_image(image)
					# TODO: synthesize initial pointer and keyboard events
		
		async def close(self):
			"Close current document, reverting to default state."
			
			async with self.lock:
				if self.main_url is not None:
					self.main_url = None
					await self.model.close_document(self)
					if self.auto_show:
						self.set_image(None)
		
		def set_image(self, image):
			"Directly set image to display (document returned by `model.create_document`). None to unset."
			
			self.model.set_image(self, image)
		
		def draw_image(self, model):
			"Draw the currently opened image to a Cairo surface. Returns the rendered surface. `model` argument is to allow multi-model widgets."
			
			viewport_width = model.get_viewport_width(self)
			viewport_height = model.get_viewport_height(self)
			
			surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, (0, 0, viewport_width, viewport_height)) # more memory friendly, but slower
			#surface = cairo.ImageSurface(cairo.Format.ARGB32, viewport_width, viewport_height) # faster, but uses more memory (as much as unscaled image size, which can lead to exploits)
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
		
		def poke_image(self, model, px, py):
			"Simulate pointer event at widget coordinates (px, py). Returns a list of nodes under the provided point and coordinates (qx, qy) after Cairo context transformations."
			
			viewport_width = model.get_viewport_width(self)
			viewport_height = model.get_viewport_height(self)
			
			surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, (0, 0, viewport_width, viewport_height))
			context = cairo.Context(surface)
			
			qx, qy = px, py
			nop = []
			
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
					
					qx, qy = context.device_to_user(px, py)
					nop = model.poke_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh), px, py)
				
				except NotImplementedError as error:
					model.emit_warning(self, f"NotImplementedError: {error}", image)
					pass
			
			surface.finish()
			return nop, qx, qy


if __name__ == '__main__':
	from asyncio import run, Lock, get_running_loop, create_task
	if 'Path' not in globals(): from aiopath import Path
	
	from guixmpp.mainloop import *
	
	loop_init()
	
	window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
	window.set_title("SVG test widget")
	widget = DOMWidget(keyboard_input=True, pointer_input=True, file_download=True, http_download=True, auto_show=False, chrome='chrome')
	window.add(widget)
	
	window.connect('destroy', lambda window: loop_quit())
	
	event_lock = Lock()
	
	@asynchandler
	async def dom_event(widget, event, target):
		global images, image_index
		
		if event.type_ == 'warning':
			print(event.type_, event.detail)
		elif event.type_ == 'open':
			print("open:", event.detail)
			target.set_image(target.model.current_document(target))
			return None
		elif event.type_ == 'close':
			widget.set_image(None)
			return None
		elif event.type_ == 'download':
			#if event.detail.startswith('http:') or event.detail.startswith('https:'):
			#	return False
			return True
		elif event.type_ == 'keydown':
			if event.code == 'Escape':
				async with event_lock:
					await widget.close()
					window.close()
				return None
			elif (event.code == 'Left') and images:
				async with event_lock:
					image_index -= 1
					image_index %= len(images)
					await widget.open(images[image_index])
				return None
			elif (event.code == 'Right') and images:
				async with event_lock:
					image_index += 1
					image_index %= len(images)
					await widget.open(images[image_index])
				return None
		
		#await target.dispatchEvent(event)
		#if event.defaultPrevented:
		#	return False
	
	widget.connect('dom_event', dom_event)
	
	images = []
	image_index = 0
	
	#'''
	async def main():
		"Display images from local directory, switch using left-right cursor key."
		global images, image_index, model
		DOMEvent._time = get_running_loop().time
		async for dir_ in (Path.cwd() / 'examples').iterdir():
			async for doc in dir_.iterdir():
				if doc.suffix not in ('.css', '.svg_'):
					images.append(doc.as_uri())
		images.sort(key=(lambda x: x.lower()))
		await widget.open(images[image_index])
		window.show_all()
		print("start")
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		print("stop")
		window.hide()
	#'''
	
	'''
	async def main():
		"Display image from http url."
		DOMEvent._time = get_running_loop().time
		for n in range(219):
			images.append(f'https://www.w3.org/Consortium/Offices/Presentations/SVG/{n}.svg')
		await widget.open(images[image_index])
		window.show_all()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		window.hide()
	#'''
	
	'''
	async def main():
		"Display images from profile directory."
		global images, image_index, model		
		async for doc in (Path.cwd() / 'profile').iterdir():
			if doc.suffix not in ('.css', '.svg_'):
				images.append(doc.as_uri())
		images.sort(key=(lambda x: x.lower()))
		await widget.open_document(images[image_index])
		window.show_all()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		window.hide()
	#'''
	
	run(main())
