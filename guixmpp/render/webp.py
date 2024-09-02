#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'WEBPRender',


if __name__ == '__main__':
	import sys
	del sys.path[0]


import cairo
import webp


class WEBPImage:
	def __init__(self, arr):
		self.arr = arr


class WEBPRender:
	def create_document(self, data, mime_type):
		if mime_type == 'image/webp':
			webp_data = webp.WebPData.from_buffer(data)
			arr = webp_data.decode(color_mode=webp.WebPColorMode.BGRA)
			return WEBPImage(arr)
			#w = arr.shape[1]
			#h = arr.shape[0]
			#s = arr.shape[1] * arr.shape[2]
			#ba = bytearray(arr.tobytes())
			#ba = arr.data
			#return WEBPImage(cairo.ImageSurface.create_for_data(ba, cairo.Format.ARGB32, w, h, s), w, h)
		else:
			return NotImplemented
	
	def is_webp_document(self, document):
		return isinstance(document, WEBPImage)
	
	def scan_document_links(self, document):
		if self.is_webp_document(document):
			return []
		else:
			return NotImplemented
	
	def image_dimensions(self, view, document):
		if self.is_webp_document(document):
			return document.arr.shape[1], document.arr.shape[0]
		else:
			return NotImplemented
	
	def image_width_for_height(self, view, document, height):
		if not self.is_webp_document(document):
			return NotImplemented
		p_width, p_height = self.image_dimensions(view, document)
		return height * p_width / p_height
	
	def image_height_for_width(self, view, document, width):
		if not self.is_webp_document(document):
			return NotImplemented
		p_width, p_height = self.image_dimensions(view, document)
		return width * p_height / p_width
	
	def draw_image(self, view, document, ctx, box):
		if not self.is_webp_document(document):
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
		
		surface = cairo.ImageSurface.create_for_data(document.arr.data, cairo.Format.ARGB32, document.arr.shape[1], document.arr.shape[0], document.arr.shape[1] * document.arr.shape[2])
		ctx.set_source_surface(surface)
		#ctx.rectangle(0.1, 0.1, w - 0.2, h - 0.2) # FIXME: workaround; for some reason the surface is not drawn when origin is 0, 0 (incl. translation)
		#ctx.fill()
		ctx.paint()
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.restore()
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_webp_document(document):
			return NotImplemented
		
		x, y, w, h = box
		qx, qy = ctx.device_to_user(px, py)
		hover_nodes = []
		if x <= qx <= x + w and y <= qy <= y + h and ctx.in_clip(qx, qy):
			hover_nodes.insert(0, document)
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
