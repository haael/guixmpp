#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PixbufRender',


import gi
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')

from gi.repository import GdkPixbuf, GLib, Gdk
from collections import defaultdict


class PixbufRender:
	"Supports many image formats through GdkPixbuf library."
	
	def create_document(self, data, mime_type):
		assert isinstance(mime_type, str)
		
		try:
			loader = GdkPixbuf.PixbufLoader.new_with_mime_type(mime_type)
		except GLib.Error:
			return NotImplemented
		else:
			loader.write(data)
			loader.close()
			return loader.get_pixbuf()
	
	def create_document_from_bytes(self, data, mime_type):
		try:
			loader = GdkPixbuf.PixbufLoader.new_with_mime_type(mime_type)
		except GLib.Error:
			return NotImplemented
		else:
			loader.write(data)
			loader.close()
			return loader.get_pixbuf()
	
	def create_document_from_iter(self, iter_, mime_type):
		try:
			loader = GdkPixbuf.PixbufLoader.new_with_mime_type(mime_type)
		except GLib.Error:
			return NotImplemented
		else:
			for data in iter_:
				loader.write(data)
			loader.close()
			return loader.get_pixbuf()
	
	async def create_document_from_aiter(self, aiter_, mime_type):
		try:
			loader = GdkPixbuf.PixbufLoader.new_with_mime_type(mime_type)
		except GLib.Error:
			return NotImplemented
		else:
			async for data in aiter_:
				loader.write(data) # TODO: run in executor
			loader.close()
			return loader.get_pixbuf()
	
	def is_image_document(self, document):
		return isinstance(document, GdkPixbuf.Pixbuf)
	
	def scan_document_links(self, document):
		if self.is_image_document(document):
			return []
		else:
			return NotImplemented
	
	def image_dimensions(self, view, document):
		if self.is_image_document(document):
			return document.get_width(), document.get_height()
		else:
			return NotImplemented
	
	def image_width_for_height(self, view, document, height):
		if not self.is_image_document(document):
			return NotImplemented
		p_width, p_height = self.image_dimensions(view, document)
		return height * p_width / p_height
	
	def image_height_for_width(self, view, document, width):
		if not self.is_image_document(document):
			return NotImplemented
		p_width, p_height = self.image_dimensions(view, document)
		return width * p_height / p_width
	
	def draw_image(self, view, document, ctx, box):
		if not self.is_image_document(document):
			return NotImplemented
		
		vw = self.get_viewport_width(view)
		vh = self.get_viewport_height(view)
		
		w, h = self.image_dimensions(view, document)
		x, y, ww, hh = box
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.save()
			if x != 0 or y != 0:
				ctx.translate(x, y)
			if ww != w or hh != h:
				ctx.scale(ww / w, hh / h)
		ctx.set_source_surface(Gdk.cairo_surface_create_from_pixbuf(document, 0, None))
		ctx.rectangle(0, 0, w, h)
		ctx.fill()
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.restore()
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_image_document(document):
			return NotImplemented
		
		x, y, w, h = box
		qx, qy = ctx.device_to_user(px, py)
		hover_nodes = []
		if x <= qx <= x + w and y <= qy <= y + h and ctx.in_clip(qx, qy):
			hover_nodes.insert(0, document)
		return hover_nodes
	
	def element_tabindex(self, document, element):
		if self.is_image_document(document):
			return None
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("pixbuf image")
	
	model = PixbufRender()
	
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		for filepath in example.iterdir():
			if filepath.suffix == '.png':
				mime_type = 'image/png'
			elif filepath.suffix in ['.jpg', '.jpeg']:
				mime_type = 'image/jpeg'
			elif filepath.suffix == '.svg':
				mime_type = 'image/svg'
			elif filepath.suffix == '.bmp':
				mime_type = 'image/bmp'
			else:
				continue
			document = model.create_document(filepath.read_bytes(), mime_type)
			#print(filepath, type(document))
			assert model.is_image_document(document)

