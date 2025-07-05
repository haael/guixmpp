#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PlainFormat',


from io import BytesIO
import cairo
import PIL


if __name__ == '__main__':
	from guixmpp.escape import Escape
else:
	from ..escape import Escape


class PlainFormat:
	def create_document(self, data:bytes, mime_type):
		if mime_type == 'application/octet-stream':
			return data
		
		else:
			return NotImplemented
	
	def destroy_document(self, document):
		if not self.is_plain_document(document):
			return NotImplemented
	
	def save_document(self, document, fileobj=None):
		if self.is_plain_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			fileobj.write(document)
			return fileobj
		else:
			return NotImplemented
	
	def is_plain_document(self, document):
		return isinstance(document, bytes)
	
	def scan_document_links(self, document):
		if self.is_plain_document(document):
			return []
		else:
			return NotImplemented
	
	def draw_image(self, view, document, ctx, box, callback):
		if self.is_plain_document(document):
			if callback: callback(Escape.begin_draw, document)
			
			left, top, width, height = box
			
			data = bytes().join(bytes([0, 0, 0, 0]) if _b & (1 << _c) else bytes([255, 255, 255, 0]) for _c in range(8) for _b in document)
			h = int(ceil(len(document) / width)) if width > 0 else 0
			try:
				pixels = PIL.Image.frombytes('RGBa', (int(width), h), data).tobytes()
			except ValueError:
				if callback: callback(Escape.end_draw, document)
				return
			pixels += bytes(0 for _n in range(int(4 * width * h - len(pixels))))
			image = cairo.ImageSurface.create_for_data(bytearray(pixels), cairo.FORMAT_RGB24, int(width), h)
			
			ctx.set_source_surface(image, 0, 0)
			ctx.paint()
			
			if callback: callback(Escape.end_draw, document)
		
		else:
			return NotImplemented
	
	def poke_image(self, view, document, ctx, box, px, py, callback):
		if self.is_plain_document(document):
			if callback:
				callback(Escape.begin_poke, document)
				callback(Escape.end_poke, document)
			return []
		else:
			return NotImplemented
	
	def image_dimensions(self, view, document):
		if self.is_plain_document(document):
			return 16 * 45 + 2, 16 + 2
		else:
			return NotImplemented
	
	def image_height_for_width(self, view, document, width):
		if self.is_plain_document(document):
			return 16 * 45 + 2
		
		else:
			return NotImplemented
	
	def image_width_for_height(self, view, document, height):
		if self.is_plain_document(document):
			return 16 + 2
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	print("plain format")
	
	model = PlainFormat()
	
	b = model.create_document(b'hello,void', 'application/octet-stream')
	assert model.save_document(b).getvalue() == b'hello,void'

