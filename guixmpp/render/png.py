#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PNGRender',


import cairo
from io import BytesIO
from collections import defaultdict


if __name__ == '__main__':
	from guixmpp.escape import Escape
else:
	from ..escape import Escape


class PNGImage:
	def __init__(self, surface, width, height):
		self.surface = surface
		self.width = width
		self.height = height


class PNGRender:
	"Supports creating and rendering PNG images, using Cairo only."
	
	def create_document(self, data, mime_type):
		if mime_type == 'image/png':
			s = cairo.ImageSurface.create_from_png(BytesIO(data))
			return PNGImage(s, s.get_width(), s.get_height())
		else:
			return NotImplemented
	
	def destroy_document(self, document):
		if not self.is_png_document(document):
			return NotImplemented
		document.surface.finish()
	
	def is_png_document(self, document):
		return isinstance(document, PNGImage)
	
	def scan_document_links(self, document):
		if self.is_png_document(document):
			return []
		else:
			return NotImplemented
	
	def image_dimensions(self, view, document):
		if self.is_png_document(document):
			return document.width, document.height
		else:
			return NotImplemented
	
	def image_width_for_height(self, view, document, height):
		if not self.is_png_document(document):
			return NotImplemented
		p_width, p_height = self.image_dimensions(view, document)
		return height * p_width / p_height
	
	def image_height_for_width(self, view, document, width):
		if not self.is_png_document(document):
			return NotImplemented
		p_width, p_height = self.image_dimensions(view, document)
		return width * p_height / p_width
	
	def draw_image(self, view, document, ctx, box, callback):
		if not self.is_png_document(document):
			return NotImplemented
		
		if callback: callback(Escape.begin_draw, document)
		
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
		ctx.set_source_surface(document.surface)
		#ctx.rectangle(0.1, 0.1, w - 0.2, h - 0.2) # FIXME: workaround; for some reason the surface is not drawn when origin is 0, 0 (incl. translation)
		#ctx.fill()
		ctx.paint()
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.restore()
		
		if callback: callback(Escape.end_draw, document)
	
	def poke_image(self, view, document, ctx, box, px, py, callback):
		if not self.is_png_document(document):
			return NotImplemented
		
		if callback: callback(Escape.begin_poke, document)
		x, y, w, h = box
		qx, qy = ctx.device_to_user(px, py)
		hover_nodes = []
		if x <= qx <= x + w and y <= qy <= y + h and ctx.in_clip(qx, qy):
			hover_nodes.insert(0, document)
		if callback: callback(Escape.end_poke, document)
		return hover_nodes
	
	def element_tabindex(self, document, element):
		if self.is_png_document(document):
			return None
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("png image")
	
	model = PNGRender()
	
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		for filepath in example.iterdir():
			if filepath.suffix == '.png':
				mime_type = 'image/png'
			else:
				continue
			document = model.create_document(filepath.read_bytes(), mime_type)
			assert model.is_png_document(document)
