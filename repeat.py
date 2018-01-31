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

import base64
import binascii
import hashlib

#import sleekxmpp





class Repeat(gtk.Container):
	__gtype_name__ = 'Repeat'
	
	__gproperties__ = {
		'model' : (gobject.TYPE_PYOBJECT, "model", "List of dicts - data to display.", gobject.PARAM_READWRITE)
	}
	
	def do_get_property(self, prop):
		if prop.name == 'model':
			return self.get_model()
		else:
			raise AttributeError("Unknown property %s" % prop.name)
	
	def do_set_property(self, prop, value):
		if prop.name == 'model':
			self.set_model(value)
		else:
			raise AttributeError("Unknown property %s" % prop.name)
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.child = None
		self.box = gtk.Box()
		self.box.set_name('__Repeat.box')
		self.box.set_orientation(gtk.Orientation.VERTICAL)
		self.box.set_parent(self)
		self.model = []
	
	def set_orientation(self, orientation):
		self.box.set_orientation(orientation)
	
	def get_orientation(self):
		return self.box.get_orientation()
	
	def clone(self, widget):
		new_widget = widget.__class__()
		
		if __debug__: children_count = 0
		try:
			for child in widget.get_children():
				if __debug__: children_count += 1
				if child.get_name() == '__Repeat.box': continue
				new_child = self.clone(child)
				new_widget.add(new_child)
				if hasattr(widget, 'query_child_packing') and hasattr(widget, 'set_child_packing'):
					new_widget.set_child_packing(new_child, *widget.query_child_packing(child))
		except AttributeError:
			pass
		
		for prop in widget.props:
			try:
				if prop.name == 'parent': continue
				new_widget.set_property(prop.name, widget.get_property(prop.name))
				assert len(new_widget.get_children()) == children_count # we mustn`t set properties that add children
			except TypeError:
				pass
			except NotImplementedError:
				pass
			except AttributeError:
				pass
		
		return new_widget
	
	def set_model(self, model):
		self.model = model
		self.update_model()
	
	def get_model(self):
		return self.model
	
	def update_model(self):
		if self.child is None:
			return
		
		for child in self.box.get_children():
			self.box.remove(child)
		
		for line in self.model:
			child = self.clone(self.child)
			for name, value in line.items():
				dstchild = child
				path = name.split('.')
				for pel in path[:-1]:
					try:
						for candchild in dstchild.get_children():
							if candchild.get_name() == pel:
								dstchild = candchild
								break
						else:
							pass
					except AttributeError: #dstchild.get_children
						pass
				dstchild.set_property(path[-1], value)
			self.box.pack_start(child, True, True, 0)
		
		self.queue_resize()
	
	def do_child_type(self):
		return(gtk.Widget.get_type())
	
	def do_add(self, widget):
		if self.box is widget:
			return
		if self.child:
			raise ValueError("Child already added ('%s' vs. '%s')" % (self.child.get_name(), widget.get_name()))
		self.child = widget
		self.child.set_parent(self)
		self.queue_resize()
	
	def do_remove(self, widget):
		if self.box is widget:
			return
		if self.child is not widget:
			raise ValueError("Child not added")
		widget_was_visible = self.child.get_visible()
		self.child.unparent()
		self.child = None
		if widget_was_visible:
			self.queue_resize()
	
	def do_forall(self, include_internals, callback, *callback_data):
		#print("do_forall", include_internals)
		try:
			callback(self.box, *callback_data)
			if self.child:
				callback(self.child, *callback_data)
		except AttributeError:
			pass
	
	def do_realize(self):
		#print("do_realize")
		allocation = self.get_allocation()
		
		attr = gdk.WindowAttr()
		attr.window_type = gdk.WindowType.CHILD
		attr.x = allocation.x
		attr.y = allocation.y
		attr.width = allocation.width
		attr.height = allocation.height
		attr.visual = self.get_visual()
		attr.event_mask = self.get_events() | gdk.EventMask.EXPOSURE_MASK
		
		WAT = gdk.WindowAttributesType
		mask = WAT.X | WAT.Y | WAT.VISUAL
		
		window = gdk.Window(self.get_parent_window(), attr, mask);
		window.set_decorations(0)
		self.set_window(window)
		self.register_window(window)
		self.set_realized(True)

		self.box.set_parent_window(window)
		#self.box.set_parent_window(window)
	
	def do_get_request_mode(self):
		#print("do_get_request_mode")
		return gtk.SizeRequestMode.CONSTANT_SIZE

	def do_get_preferred_height(self):
		height = self.box.get_preferred_height()
		#print("do_get_preferred_height", height)
		return height

	def do_get_preferred_width(self):
		width = self.box.get_preferred_width()
		#print("do_get_preferred_width", width)
		return width
	
	def do_size_allocate(self, allocation):
		#print("do_size_allocate", allocation.x, allocation.y, allocation.width, allocation.height)
		self.set_allocation(allocation)
		if self.get_has_window() and self.get_realized():
			self.get_window().move_resize(allocation.x, allocation.y, allocation.width, allocation.height)
		if self.box and self.box.get_visible():
			child_allocation = gdk.Rectangle()
			child_allocation.width = allocation.width
			child_allocation.height = allocation.height
			self.box.size_allocate(child_allocation)
	
	def do_draw(self, cr):
		#print("do_draw")
		allocation = self.get_allocation()
		gtk.render_background(self.get_style_context(), cr, 0, 0, allocation.width, allocation.height)
		self.propagate_draw(self.box, cr)


if __name__ == '__main__':
	glib.threads_init()
	
	css = gtk.CssProvider()
	css.load_from_path('style.css')
	gtk.StyleContext().add_provider_for_screen(gdk.Screen.get_default(), css, gtk.STYLE_PROVIDER_PRIORITY_USER)
	
	window = gtk.Window()
	repeat = Repeat()
	box = gtk.Box()
	#box.set_orientation(gtk.Orientation.VERTICAL)
	button1 = gtk.Button()
	button1.set_name("button1")
	box.pack_start(button1, True, True, 0)

	repeat2 = Repeat()
	repeat2.set_orientation(gtk.Orientation.VERTICAL)
	repeat2.set_name("repeat2")

	label1 = gtk.Button()
	label1.set_name("label1")
	repeat2.add(label1)

	box.pack_start(repeat2, True, True, 0)
	repeat.add(box)
	#print(button1.path(), button2.path())
	#repeat.add(gtk.Button("buka"))
	repeat.set_model([{'button1.label':"1111", 'repeat2.model':[{'label1.label':"1a"}]}, {'button1.label':"2222", 'repeat2.model':[{'label1.label':"2a"}, {'label1.label':"2b"}]}, {"button1.label":"3333", 'repeat2.model':[{'label1.label':"3a"}, {'label1.label':"3b"}, {'label1.label':"3c"}]}])
	window.add(repeat)

	#print(repeat.get_children())
	
	mainloop = gobject.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())
	window.connect('destroy', lambda widget: mainloop.quit())	
	window.show_all()
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()


