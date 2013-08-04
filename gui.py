#!/usr/bin/python3
#-*- coding: utf-8 -*-

from __future__ import unicode_literals


import copy
import io

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import GLib as glib

import rsvg
import cairo



def bind(view, model):
	model._Model__view = view
	view._View__model = model

def unbind(view, model):
	model._Model__view = None
	view._View__model = None


class LocalModel:
	def __init__(self):
		self.__items = {}
	
	def __update(self):
		self.__generate_svg('drawingarea1')
		#print(self.__items)
		self.__view._View__update()
	
	def __generate_svg(self, name):
		try:
			node = self[name]
		except KeyError:
			return
		
		try:
			width = node['width']
			height = node['height']
		except KeyError:
			width = 0
			height = 0
		
		svgbuffer = io.BytesIO()
		surface = cairo.SVGSurface(svgbuffer, width, height)
		
		ctx = cairo.Context(surface)
		ctx.set_source_rgb(0, 0, 0)
		ctx.paint()
		ctx.set_source_rgb(1, 1, 1)
		ctx.set_line_width(20)
		ctx.rectangle(100, 100, width - 200, height - 200)
		ctx.stroke()

		ctx.set_source_rgb(0, 0, 1)
		ctx.set_line_width(1)
		ctx.rectangle(121, 121, width - 242, height - 242)
		try:
			state = self['togglebutton1']['active']
		except KeyError:
			state = False
		if state:
			ctx.fill()
		else:
			ctx.stroke()
		
		try:
			text = self['entry1']['text']
			ctx.set_source_rgb(1, 1, 1)
			ctx.set_font_size(20)
			ctx.move_to(130, height / 2)
			ctx.text_path(text)
			ctx.fill()
		except KeyError:
			pass
		
		surface.finish()
		node['svg'] = svgbuffer.getvalue()
	
	def __getitem__(self, key):
		try:
			return self.__items[key]
		except KeyError:
			node = {}
			self.__items[key] = node
			return node
	
	def __setitem__(self, key, value):
		self.__items[key] = value
	
	def __delitem__(self, key):
		del self.__items[key]
	
	def __iter__(self):
		for name in self.__items.keys():
			yield name


class RemoteModel:
	class Interceptor:
		def __init__(self, parent, items={}):
			self.__parent = parent
			self.__items = copy.deepcopy(items)
		
		def __getitem__(self, key):
			return self.__items[key]
		
		def __setitem__(self, key, value):
			if value is None:
				del self[key]
			else:
				self.__items[key] = value
		
		def __delitem__(self, key):
			del self.__items[key]
		
		def __getattr__(self, attr):
			def method(widget, *args, **kwargs):
				print(widget, attr, args, kwargs)
				self.__parent._RemoteModel__xmpp.event("gui_emit_signal", (self.__parent._RemoteModel__jid, widget, attr, args, kwargs))
			method.name = attr
			return method
		
		def __repr__(self):
			return repr(self.__items)
		
		def __bool__(self):
			return bool(self.__items)
	
	def __init__(self, xmpp, jid):
		self.__xmpp = xmpp
		self.__jid = jid
		self.__items = {}
		self.__changes = {}
	
	def _Model__update(self):
		todel = [key for (key, value) in self.__changes.items() if (not value) and (value is not None)]
		for key in todel:
			del self.__changes[key]
		if self.__changes:
			self.__xmpp.event("gui_update_model", (self.__jid, self.__changes))
		self.__changes = {}
	
	def __receive_updated(self, changes):
		self.__items.update(changes)
		self.__view._View__update()
	
	def __getitem__(self, key):
		try:
			node = self.__items[key]
			self.__changes[key] = node
			return node
		except KeyError:
			node = self.Interceptor(self)
			self.__changes[key] = node
			self.__items[key] = node
			return node
	
	def __setitem__(self, key, value):
		if value is None:
			del self[key]
		else:
			#node = self.Interceptor(self, value)
			self.__changes[key] = value
			self.__items[key] = value
	
	def __delitem__(self, key):
		self.__changes[key] = None
		del self.__items[key]
	
	def __iter__(self):
		for name in self.__items.keys():
			yield name


class View:
	def __init__(self, path=None, data=None):
		self.__svg_handles = {}
		self.__builder = gtk.Builder()
		if path is not None:
			self.__builder.add_from_file(path)
		elif data is not None:
			self.__builder.add_from_string(data)
		else:
			raise ValueError("Provide path or string with UI description")
		self.__builder.connect_signals(self)
	
	def __getitem__(self, attr):
		return self.__builder.get_object(attr)
	
	def __getattr__(self, attr):
		def handle_event(widget, *args):
			name = gtk.Buildable.get_name(widget)
			method = getattr(self.__model[name], attr, (lambda w, *a, **k: print("unhandled event:", attr, w, a, k)))
			kwargs = {}
			for a in ['name', 'visible', 'has-default', 'has-focus', 'is-focus', 'active']:
				try:
					kwargs[a] = widget.get_property(a)
				except TypeError:
					pass
			method(name, *args, **kwargs)
			self.__model._Model__update()
		handle_event.name = attr
		return handle_event
	
	def on_svg_draw(self, widget, ctx):
		ctx.set_source_rgb(0, 0, 0)
		ctx.paint()
		ctx.scale(0.8, 0.8)
		try:
			self.__svg_handles[gtk.Buildable.get_name(widget)].render_cairo(ctx)
		except KeyError:
			pass
	
	def on_size_allocate(self, widget, allocation):
		node = self.__model[gtk.Buildable.get_name(widget)]
		node['width'] = allocation.width
		node['height'] = allocation.height
		self.__model._Model__update()
	
	def on_editable_changed(self, widget):
		node = self.__model[gtk.Buildable.get_name(widget)]
		node['text'] = widget.get_buffer().get_text()
		self.__model._Model__update()
	
	def on_togglebutton_toggled(self, widget):
		node = self.__model[gtk.Buildable.get_name(widget)]
		node['active'] = widget.get_active()
		self.__model._Model__update()
	
	def on_combobox_changed(self, widget):
		node = self.__model[gtk.Buildable.get_name(widget)]
		node['index'] = widget.get_active()
		self.__model._Model__update()
	
	def on_range_value_changed(self, widget, value):
		node = self.__model[gtk.Buildable.get_name(widget)]
		node['value'] = value
		self.__model._Model__update()
	
	def __update(self):
		for name in self.__model:
			node = self.__model[name]
			
			if 'svg' in node:
				self.__svg_handles[name] = rsvg.Handle(data=node['svg'])
				self[name].queue_draw()


def handle_ui_description(xmpp, jid, uidesc):
	view = View(data=uidesc)
	model = RemoteModel(xmpp, jid)
	bind(view, model)
	def close_application(window):
		xmpp.event("gui_close_application", jid)
		unbind(view, model)
	view['main_window'].connect('destroy', close_application)
	view['main_window'].show()
	return model


if __name__ == '__main__':
	import signal
	
	glib.threads_init()
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	
	with open("bunch.glade") as ui:
		handle_ui_description("aaa@example.net", ui.read())
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()
	







