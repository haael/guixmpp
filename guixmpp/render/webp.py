#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'WEBPRender',


if __name__ == '__main__':
	import sys
	del sys.path[0]


import cairo
import webp


if __name__ == '__main__':
	from guixmpp.escape import Escape
else:
	from ..escape import Escape


class WEBPImage:
	def __init__(self, width, height, array, surface):
		self.width = width
		self.height = height
		self.array = array
		self.surface = surface


class WEBPRender:
	def create_document(self, data, mime_type):
		if mime_type == 'image/webp':
			webp_data = webp.WebPData.from_buffer(data)
			array = webp_data.decode(color_mode=webp.WebPColorMode.BGRA)
			w = array.shape[1]
			h = array.shape[0]
			
			# Cairo expects premultiplied pixel values.
			array[:, :, 0] = (array[:, :, 0] * (array[:, :, 3] / 255.0)).astype(array.dtype)
			array[:, :, 1] = (array[:, :, 1] * (array[:, :, 3] / 255.0)).astype(array.dtype)
			array[:, :, 2] = (array[:, :, 2] * (array[:, :, 3] / 255.0)).astype(array.dtype)
			
			surface = cairo.ImageSurface.create_for_data(array.data.cast('B'), cairo.Format.ARGB32, w, h)
			return WEBPImage(w, h, array, surface)
		else:
			return NotImplemented
	
	def destroy_document(self, document):
		if not self.is_webp_document(document):
			return NotImplemented
		document.surface.finish()
	
	def is_webp_document(self, document):
		return isinstance(document, WEBPImage)
	
	def scan_document_links(self, document):
		if self.is_webp_document(document):
			return []
		else:
			return NotImplemented
	
	def image_dimensions(self, view, document, callback):
		if self.is_webp_document(document):
			return document.width, document.height
		else:
			return NotImplemented
	
	def image_width_for_height(self, view, document, height, callback):
		if not self.is_webp_document(document):
			return NotImplemented
		p_width, p_height = self.image_dimensions(view, document, callback)
		return height * p_width / p_height
	
	def image_height_for_width(self, view, document, width, callback):
		if not self.is_webp_document(document):
			return NotImplemented
		p_width, p_height = self.image_dimensions(view, document, callback)
		return width * p_height / p_width
	
	def draw_image(self, view, document, ctx, box, callback):
		if not self.is_webp_document(document):
			return NotImplemented
		
		if callback: callback(Escape.begin_draw, document)
		
		vw = self.get_viewport_width(view)
		vh = self.get_viewport_height(view)
		
		w, h = self.image_dimensions(view, document, callback)
		x, y, ww, hh = box
		
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.save()
			if x != 0 or y != 0:
				ctx.translate(x, y)
			if ww != w or hh != h:
				ctx.scale(ww / w, hh / h)
		
		ctx.set_source_surface(document.surface)
		ctx.paint()
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.restore()
		
		if callback: callback(Escape.end_draw, document)
	
	def poke_image(self, view, document, ctx, box, px, py, callback):
		if not self.is_webp_document(document):
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
		if self.is_webp_document(document):
			return None
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("webp image")
	
	model = WEBPRender()
	
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		for filepath in example.iterdir():
			if filepath.suffix == '.webp':
				mime_type = 'image/webp'
			else:
				continue
			document = model.create_document(filepath.read_bytes(), mime_type)
			assert model.is_webp_document(document)
