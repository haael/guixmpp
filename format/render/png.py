#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PNGFormat',


import cairo
from io import BytesIO


class PNGFormat:
	"Supports creating and rendering PNG images, using Cairo only."
	
	def create_document(self, data, mime_type):
		if mime_type == 'image/png':
			return cairo.ImageSurface.create_from_png(BytesIO(data))
		else:
			return NotImplemented
	
	def is_png_document(self, document):
		return isinstance(document, cairo.ImageSurface)
	
	def scan_document_links(self, document):
		if self.is_png_document(document):
			return []
		else:
			return NotImplemented
	
	#def transform_document(self, document):
	#	if self.is_png_document(document):
	#		return document
	#	else:
	#		return NotImplemented
	
	def image_dimensions(self, view, document):
		if self.is_png_document(document):
			return document.get_width(), document.get_height()
		else:
			return NotImplemented
	
	def draw_image(self, view, document, ctx, box):
		if not self.is_png_document(document):
			return NotImplemented
		
		vw = view.widget_width
		vh = view.widget_height
		
		w, h = self.image_dimensions(view, document)
		x, y, ww, hh = box
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.save()
			if x != 0 or y != 0:
				ctx.translate(x, y)
			if ww != w or hh != h:
				ctx.scale(ww / w, hh / h)
		ctx.set_source_surface(document)
		ctx.rectangle(0, 0, w, h)
		ctx.fill()
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.restore()
		
		return []
	
	def element_tabindex(self, document, element):
		if self.is_png_document(document):
			return None
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("png format")	
	
	model = PNGFormat()
	
	for filepath in Path('gfx').iterdir():
		if filepath.suffix == '.png':
			mime_type = 'image/png'
		else:
			continue
		document = model.create_document(filepath.read_bytes(), mime_type)
		assert model.is_png_document(document)
