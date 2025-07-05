#!/usr/bin/python3
#-*- coding:utf-8 -*-


"Imagecodecs renderer. Supports the following formats: TIFF, MDI, APNG, PNG, GIF, WEBP, JPEG8, LJPEG, JPEG 2K, JPEG LS, JPEG XR, JPEG XL, AVIF, BMP, ULTRAHDR, ZFP, LERC, RGBE."


__all__ = 'ImageRender',


if __name__ == '__main__':
	import sys
	del sys.path[0]


import cairo
from imagecodecs import imread
from io import BytesIO
from numpy import full, concatenate, flip


if __name__ == '__main__':
	from guixmpp.escape import Escape
else:
	from ..escape import Escape


class ImageDocument:
	def __init__(self, width, height, array, surface):
		self.width = width
		self.height = height
		self.array = array
		self.surface = surface


class ImageRender:
	"Decodes some formats (JPEG in particular) using imagecodecs library."
	
	def create_document(self, data, mime_type):
		if data is not None and mime_type.startswith('image/'):
			try:
				pixels = imread(BytesIO(data)) # do the decoding
			except ValueError:
				pass
			else:
				# FIXME: JPEG XL doesn't work
				
				if pixels.shape[2] == 3: # RGB image
					width = pixels.shape[1]
					height = pixels.shape[0]
					alpha_channel = full((height, width, 1), 255, dtype=pixels.dtype)
					pixels = concatenate((flip(pixels, axis=2), alpha_channel), axis=2)
					surface = cairo.ImageSurface.create_for_data(pixels.data.cast('B'), cairo.Format.RGB24, width, height)
					return ImageDocument(width, height, pixels, surface)
				
				elif pixels.shape[2] == 4: # RGBA image
					width = pixels.shape[1]
					height = pixels.shape[0]
					array = pixels[:, :, [2, 1, 0, 3]].copy()
					
					# Cairo expects premultiplied pixel values.
					array[:, :, 0] = (array[:, :, 0] * (array[:, :, 3] / 255.0)).astype(array.dtype)
					array[:, :, 1] = (array[:, :, 1] * (array[:, :, 3] / 255.0)).astype(array.dtype)
					array[:, :, 2] = (array[:, :, 2] * (array[:, :, 3] / 255.0)).astype(array.dtype)
					
					surface = cairo.ImageSurface.create_for_data(array.data.cast('B'), cairo.Format.ARGB32, width, height)
					return ImageDocument(width, height, array, surface)
				
				else:
					raise ValueError
		
		return NotImplemented
	
	def destroy_document(self, document):
		if not self.is_image_document(document):
			return NotImplemented
		document.surface.finish()
	
	def is_image_document(self, document):
		return isinstance(document, ImageDocument)
	
	def scan_document_links(self, document):
		if self.is_image_document(document):
			return []
		else:
			return NotImplemented
	
	def image_dimensions(self, view, document):
		if self.is_image_document(document):
			return document.array.shape[1], document.array.shape[0]
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
	
	def draw_image(self, view, document, ctx, box, callback):
		if not self.is_image_document(document):
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
		ctx.paint()
		if x != 0 or y != 0 or ww != w or hh != h:
			ctx.restore()
		
		if callback: callback(Escape.end_draw, document)
	
	def poke_image(self, view, document, ctx, box, px, py, callback):
		if not self.is_image_document(document):
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
		if self.is_image_document(document):
			return None
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("Image codecs")
	
	model = ImageRender()
	
	for filepath in Path('examples/raster').iterdir():
		print(filepath)
		document = model.create_document(filepath.read_bytes(), 'image/*')
		if document is NotImplemented: continue
		assert model.is_image_document(document)
		print(document.array.shape)
