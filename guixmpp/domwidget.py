#!/usr/bin/python3
#-*- coding: utf-8 -*-


__all__ = 'DOMWidget',


import gi
if __name__ == '__main__':
	gi.require_version('Gtk', '4.0')
	gi.require_version('Gio', '2.0')
	gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GObject, GLib, Gio

import cairo

from enum import Enum
from math import hypot
from itertools import zip_longest, chain
from collections import namedtuple, defaultdict
from asyncio import Lock, get_event_loop, get_running_loop, run
from asyncio.exceptions import CancelledError


if __name__ == '__main__':
	from guixmpp.domevents import *
	DOMEvent = Event
	
	from guixmpp.document import Model, DocumentNotFound
	
	from guixmpp.format.null import NullFormat
	from guixmpp.format.plain import PlainFormat
	from guixmpp.format.text import TextFormat
	from guixmpp.format.xml import XMLFormat
	from guixmpp.format.css import CSSFormat
	from guixmpp.format.font import FontFormat
	from guixmpp.format.json import JSONFormat
	#from guixmpp.format.xforms import XFormsFormat
	
	from guixmpp.render.svg import SVGRender
	from guixmpp.render.png import PNGRender
	from guixmpp.render.webp import WEBPRender
	from guixmpp.render.pixbuf import PixbufRender
	from guixmpp.render.image import ImageRender
	from guixmpp.render.html2 import HTMLRender
	
	from guixmpp.script.javascript import JSFormat
	
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
	from .format.text import TextFormat
	from .format.xml import XMLFormat
	from .format.css import CSSFormat
	from .format.font import FontFormat
	from .format.json import JSONFormat
	#from .format.xforms import XFormsFormat
	
	from .render.svg import SVGRender
	from .render.png import PNGRender
	from .render.webp import WEBPRender
	from .render.pixbuf import PixbufRender
	from .render.image import ImageRender
	from .render.html2 import HTMLRender
	
	from .script.javascript import JSFormat
	
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
		
		def __init__(self, file_=None, url=None, keyboard_input=False, pointer_input=False, file_download=False, http_download=False, cid_download=False, js_script=False, chrome=None, auto_show=True):
			super().__init__()
			
			self.set_can_focus(True)
			self.set_focusable(True)
			self.lock = Lock()
			self.main_url = None
			
			self.prop_file = file_
			self.prop_url = url
			
			self.keyboard_input = keyboard_input
			self.pointer_input = pointer_input
			self.file_download = file_download
			self.http_download = http_download
			self.cid_download = cid_download
			self.js_script = js_script
			self.chrome = chrome
			self.auto_show = auto_show
			
			if hasattr(self, 'add_events'):
				self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
				self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
				self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)		
				self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
				self.add_events(Gdk.EventMask.KEY_RELEASE_MASK)
				self.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
			
			self.configure_model()
		
		def configure_model(self):
			if hasattr(self, 'model'):
				for subj, conn in self.connections:
					subj.disconnect(conn)
				for ctrl in self.controllers:
					self.remove_controller(ctrl)
				del self.model, self.connections, self.controllers
			
			features = []
			cc = []
			if self.keyboard_input:
				features.append(KeyboardView)
				cc.append('Kb')
			if self.pointer_input:
				features.append(PointerView)
				cc.append('Pt')
			if self.file_download:
				features.append(FileDownload)
				cc.append('Fl')
			if self.http_download:
				features.append(HTTPDownload)
				cc.append('Ht')
			if self.cid_download:
				features.append(CIDDownload)
				cc.append('Ci')
			if self.js_script:
				features.append(JSFormat)
				cc.append('Js')
			if self.chrome:
				features.append(ChromeDownload)
				cc.append('Ch')
			
			if cc:
				cc.insert(0, '_')
			else:
				cc.append('_X')
			
			DOMWidgetModel = Model.features('<local>.DOMWidgetModel' + ''.join(cc), DisplayView, SVGRender, PNGRender, WEBPRender, ImageRender if Gtk.get_major_version() >= 4 else PixbufRender, HTMLRender, FontFormat, *features, ResourceDownload, XMLFormat, CSSFormat, JSONFormat, TextFormat, PlainFormat, NullFormat, DataDownload)
			self.model = DOMWidgetModel(chrome_dir=self.chrome)
			
			if Gtk.get_major_version() < 4:
				self.controllers = []
				self.connections = [
					(self, self.connect('draw', self.model.draw_gtk3)),
					(self, self.connect('configure-event', self.model.handle_event_gtk3, 'display')),
					(self, self.connect('motion-notify-event', self.model.handle_event_gtk3, 'motion')),
					(self, self.connect('button-press-event', self.model.handle_event_gtk3, 'button')),
					(self, self.connect('button-release-event', self.model.handle_event_gtk3, 'button')),
					#(self, self.connect('clicked', self.model.handle_event_gtk3, 'click')),
					#(self, self.connect('auxclicked', self.model.handle_event_gtk3, 'click')),
					#(self, self.connect('dblclicked', self.model.handle_event_gtk3, 'click')),
					(self, self.connect('scroll-event', self.model.handle_event_gtk3, 'scroll')),
					(self, self.connect('key-press-event', self.model.handle_event_gtk3, 'key')),
					(self, self.connect('key-release-event', self.model.handle_event_gtk3, 'key'))
				]
			else:
				motion_controller = Gtk.EventControllerMotion.new()
				self.add_controller(motion_controller)
				
				click_controller = Gtk.GestureClick.new()
				self.add_controller(click_controller)
				
				key_controller = Gtk.EventControllerKey.new()
				self.add_controller(key_controller)
				
				scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
				self.add_controller(scroll_controller)
				
				self.controllers = [motion_controller, click_controller, key_controller, scroll_controller]
				
				self.connections = [
					# Snapshot signal for drawing
					#(self, self.connect('snapshot', self.model.draw)),
					
					# Configure event
					(self, self.connect('resize', self.model.handle_event_gtk4, 'CONFIGURE_EVENT', 'display', self)),
					
					# Motion event controller
					(motion_controller, motion_controller.connect('motion', self.model.handle_event_gtk4, 'MOTION_NOTIFY', 'motion', self)),
					
					# Button press and release event controller
					(click_controller, click_controller.connect('pressed', self.model.handle_event_gtk4, 'BUTTON_PRESS', 'button', self)),
					(click_controller, click_controller.connect('released', self.model.handle_event_gtk4, 'BUTTON_RELEASE', 'button', self)),
					
					# Clicked, auxclicked, and dblclicked are handled by Gtk.GestureClick
					#(click_controller, click_controller.connect('clicked', self.model.handle_event_gtk4, 'CLICK', 'click', self)),
					#(click_controller, click_controller.connect('secondary-clicked', self.model.handle_event_gtk4, '_2NDCLICK', 'click', self)),
					#(click_controller, click_controller.connect('unpaired-release', self.model.handle_event_gtk4, 'DBLCKICK', 'click', self)),
					
					# Key event controller
					(key_controller, key_controller.connect('key-pressed', self.model.handle_event_gtk4, 'KEY_PRESS', 'key', self)),
					(key_controller, key_controller.connect('key-released', self.model.handle_event_gtk4, 'KEY_RELEASE', 'key', self)),
					(key_controller, key_controller.connect('modifiers', self.model.handle_event_gtk4, 'MODIFIERS', 'key', self)),
					
					# Scroll event controller
					(scroll_controller, scroll_controller.connect('scroll', self.model.handle_event_gtk4, 'SCROLL_EVENT', 'scroll', self))
				]
				
				self.set_draw_func(self.model.draw_gtk4)
		
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
				coro = self.close()
			
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
				#print('DOMWidget.open', hex(id(self))[2:], url)
				if self.main_url is not None:
					await self.model.close_document(self)
				self.main_url = url
				try:
					image = await self.model.open_document(self, url)
				except CancelledError:
					print("open task cancelled")
					try:
						await self.model.close_document(self)
					except* DocumentNotFound:
						pass
					self.main_url = None
					raise
				if self.auto_show:
					self.set_image(image)
					# TODO: synthesize initial pointer and keyboard events
		
		async def close(self):
			"Close current document, reverting to default state."
			
			#print('DOMWidget.close', hex(id(self))[2:])
			async with self.lock:
				if self.main_url is not None:
					await self.model.close_document(self)
					self.main_url = None
					if self.auto_show:
						self.set_image(None)
		
		def set_image(self, image):
			"Directly set image to display (document returned by `model.create_document`). None to unset."
			self.model.set_image(self, image)
		
		def draw_image(self, model, context):
			"Draw the currently opened image to a Cairo surface. Returns the rendered surface. `model` argument is to allow multi-model widgets."
			
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
		
		def poke_image(self, model, context, px, py):
			"Simulate pointer event at widget coordinates (px, py). Returns a list of nodes under the provided point and coordinates (qx, qy) after Cairo context transformations."
			
			callback = (lambda _reason, _param: True)
			
			viewport_width = model.get_viewport_width(self)
			viewport_height = model.get_viewport_height(self)
			
			qx, qy = px, py
			nop = []
			
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
					
					qx, qy = context.device_to_user(px, py)
					nop = model.poke_image(self, image, context, ((viewport_width - bw) / 2, (viewport_height - bh) / 2, bw, bh), px, py, callback)
				
				except NotImplementedError as error:
					model.emit_warning(self, f"NotImplementedError: {error}", image)
					pass
			
			return nop, qx, qy


if __name__ == '__main__':
	from asyncio import run, Lock, get_running_loop, create_task
	from guixmpp.gtkaiopath import Path
	from guixmpp.mainloop import *
	from sys import argv, exit
	
	loop_init()
	
	window = Gtk.Window()
	window.set_title("SVG test widget")
	widget = DOMWidget(keyboard_input=True, pointer_input=True, file_download=True, http_download=True, auto_show=False, chrome='chrome', js_script=False)
	if hasattr(window, 'add'):
		window.add(widget)
	else:
		window.set_child(widget)
	
	window.set_focus(widget)
	
	window.connect('close-request', lambda window: loop_quit())
	
	event_lock = Lock()
	opening_task = None
	root_dir = None
	
	@asynchandler
	async def dom_event(widget, event, target):
		global images, image_index, opening_task
		
		if event.type_ == 'warning':
			print(event.type_, event.detail)
		#elif event.type_ == 'opening':
		#	print("opening:", event.detail)
		#	return None
		elif event.type_ == 'open':
			print("open:", event.detail)
			target.set_image(target.model.current_document(target))
			return None
		elif event.type_ == 'close':
			widget.set_image(None)
			return None
		elif event.type_ == 'download':
			if event.detail.startswith('file:') and not event.detail.startswith(root_dir.as_uri()): # do not allow file access outside the specified directory
				return False
			#if not event.detail.startswith('data:'):
			#	print("download", event.detail)
			#else:
			#	print("download", event.detail[:32], "...")
			#if event.detail.startswith('http:') or event.detail.startswith('https:'):
			#	return False
			return True
		elif event.type_ == 'keydown':
			if event.code == 'Escape':
				async with event_lock:
					print()
					await widget.close()
					window.close()
				return None
			elif (event.code == 'Left') and images:
				print()
				async with event_lock:
					image_index -= 1
					image_index %= len(images)
					if opening_task and not opening_task.done():
						opening_task.cancel()
						try:
							await opening_task
						except CancelledError:
							pass
					opening_task = create_task(widget.open(images[image_index]))
					loop_add(opening_task)
				return None
			elif (event.code == 'Right') and images:
				async with event_lock:
					print()
					image_index += 1
					image_index %= len(images)
					if opening_task and not opening_task.done():
						opening_task.cancel()
						try:
							await opening_task
						except CancelledError:
							pass
					opening_task = create_task(widget.open(images[image_index]))
					loop_add(opening_task)
				return None
		
		#await target.dispatchEvent(event)
		#if event.defaultPrevented:
		#	return False
	
	widget.connect('dom_event', dom_event)
	
	images = []
	image_index = 0
	
	async def main_1():
		"Display images from local directory, switch using left-right cursor key."
		global images, image_index, model, root_dir
		DOMEvent._time = get_running_loop().time
		root_dir = Path.cwd() / 'examples'
		async for dir_ in root_dir.iterdir():
			if not await dir_.is_dir(): continue
			if dir_.parts[-1] not in {'text', 'gfx'}: continue
			async for doc in dir_.iterdir():
				if doc.suffix not in ('.css', '.svg_', '.html', '.xhtml', '.htm', '.py'):
					images.append(doc.as_uri())
		images.sort(key=(lambda x: x.lower()))
		await widget.open(images[image_index])
		if hasattr(window, 'show_all'):
			window.show_all()
		else:
			window.present()
		print("start")
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		print("stop")
		#window.close()
	
	async def main_2():
		"Display HTML files from local directory, switch using left-right cursor key."
		global images, image_index, model, root_dir
		DOMEvent._time = get_running_loop().time
		root_dir = Path.cwd() / 'examples'
		async for dir_ in root_dir.iterdir():
			if not await dir_.is_dir(): continue
			async for doc in dir_.iterdir():
				if doc.suffix in ('.html', '.xhtml', '.htm'):
					images.append(doc.as_uri())
		images.sort(key=(lambda x: x.lower()))
		await widget.open(images[image_index])
		if hasattr(window, 'show_all'):
			window.show_all()
		else:
			window.present()
		print("start")
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		print("stop")
		#window.close()
	
	async def main_3():
		"Display image from http url."
		DOMEvent._time = get_running_loop().time
		for n in range(219):
			images.append(f'https://www.w3.org/Consortium/Offices/Presentations/SVG/{n}.svg')
		await widget.open(images[image_index])
		if hasattr(window, 'show_all'):
			window.show_all()
		else:
			window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		#window.hide()
	
	async def main_4():
		"Display images from profile directory."
		global images, image_index, model		
		async for doc in (Path.cwd() / 'profile').iterdir():
			if doc.suffix not in ('.css', '.svg_'):
				images.append(doc.as_uri())
		images.sort(key=(lambda x: x.lower()))
		await widget.open_document(images[image_index])
		if hasattr(window, 'show_all'):
			window.show_all()
		else:
			window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		#window.hide()

	async def main_5():
		global images, image_index, model, root_dir
		root_dir = Path.cwd() / 'examples'
		DOMEvent._time = get_running_loop().time
		async for doc in (root_dir / 'raster').iterdir():
			images.append(doc.as_uri())
		images.sort(key=(lambda x: x.lower()))
		await widget.open(images[image_index])
		if hasattr(window, 'show_all'):
			window.show_all()
		else:
			window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		#window.hide()
	
	async def main_6():
		global images, image_index, model, root_dir
		root_dir = Path.cwd() / 'examples'
		DOMEvent._time = get_running_loop().time
		async for doc in (root_dir / 'animations').iterdir():
			images.append(doc.as_uri())
		images.sort(key=(lambda x: x.lower()))
		await widget.open(images[image_index])
		if hasattr(window, 'show_all'):
			window.show_all()
		else:
			window.present()
		try:
			await loop_run()
		except KeyboardInterrupt:
			pass
		#window.hide()
	
	if len(argv) != 2:
		print("Pass one of arguments: --test-svg, --test-animations, --test-html, --test-tutorial, --test-profile, --test-raster.")
		exit(1)
	elif argv[1] == '--test-svg':
		run(main_1())
	elif argv[1] == '--test-html':
		run(main_2())
	elif argv[1] == '--test-tutorial':
		run(main_3())
	elif argv[1] == '--test-profile':
		run(main_4())
	elif argv[1] == '--test-raster':
		run(main_5())
	elif argv[1] == '--test-animations':
		run(main_6())
	else:
		print("Unknown argument combination.")
		exit(1)

