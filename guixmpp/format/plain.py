#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PlainFormat',


from io import BytesIO
from math import ceil, sqrt
import cairo
from re import split as re_split
from base64 import b64encode
import PIL.Image


class PlainFormat:
	def __init__(self, *args, **kwargs):
		self.__text_color = 0, 0, 0
		self.__text_font = 'sans-serif'
		self.__text_size = 16
		self.__text_spacing = 4
	
	def create_document(self, data:bytes, mime_type):
		if mime_type == 'text/plain':
			try:
				return data.decode('utf-8')
			except UnicodeDecodeError:
				print(data)
				raise
		
		elif mime_type == 'application/octet-stream':
			return data
		
		else:
			return NotImplemented
	
	def save_document(self, document, fileobj=None):
		if self.is_text_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			try:
				decoded = document.encode('utf-8')
			except UnicodeDecodeError:
				print(document)
				raise
			fileobj.write(decoded)
			return fileobj
		elif self.is_binary_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			fileobj.write(document)
			return fileobj
		else:
			return NotImplemented
	
	def is_text_document(self, document):
		return isinstance(document, str)
	
	def is_binary_document(self, document):
		return isinstance(document, bytes)
	
	def scan_document_links(self, document):
		if self.is_text_document(document) or self.is_binary_document(document):
			return []
		else:
			return NotImplemented
	
	def get_text_color(self):
		return self.__text_color
	
	def set_text_color(self, color):
		self.__text_color = color
	
	def get_text_font(self):
		return self.__text_font
	
	def set_text_font(self, font):
		self.__text_font = font
	
	def get_text_size(self):
		return self.__text_size
	
	def set_text_size(self, size):
		self.__text_size = size
	
	def get_text_spacing(self):
		return self.__text_spacing
	
	def set_text_spacing(self, spacing):
		self.__text_spacing = spacing
	
	def draw_image(self, view, document, ctx, box):
		if self.is_text_document(document):
			width = box[2]
			height = box[3]
			print("text document", width, height)
			
			ctx.rectangle(*box)
			ctx.clip()
			ctx.translate(box[0], box[1])
			
			ctx.select_font_face(self.__text_font)
			ctx.set_font_size(self.__text_size)
			
			if len(self.__text_color) == 3:
				ctx.set_source_rgb(*self.__text_color)
			elif len(self.__text_color) == 4:
				ctx.set_source_rgba(*self.__text_color)
			
			lines = []
			line = []
			offset = 0
			for word in re_split(r'[\r\n\t ]+', document):
				extents = ctx.text_extents(word)
				offset += extents.x_advance + 4
				if offset > width:
					if line:
						lines.append(" ".join(line))
					line.clear()
					line.append(word)
					offset = extents.x_advance
					if offset > width:
						lines.append(" ".join(line))
						line.clear()
						offset = 0
				else:
					line.append(word)
			if line:
				lines.append(" ".join(line))
			
			theight = len(lines) * (self.__text_size + self.__text_spacing)
			
			offset = 0
			for line in lines:
				extents = ctx.text_extents(line)
				if len(lines) > 1:
					ctx.move_to(0, offset * ((height - self.__text_size) / theight) + self.__text_size)
				else:
					ctx.move_to(0, self.__text_size)
				ctx.show_text(line)
				offset += self.__text_size + self.__text_spacing
		
		elif self.is_binary_document(document):
			left, top, width, height = box
			
			data = bytes().join(bytes([0, 0, 0, 0]) if _b & (1 << _c) else bytes([255, 255, 255, 0]) for _c in range(8) for _b in document)
			h = ceil(len(document) / width)
			pixels = PIL.Image.frombytes('RGBa', (width, h), data).tobytes()
			pixels += bytes(0 for _n in range(4 * width * h - len(pixels)))
			image = cairo.ImageSurface.create_for_data(bytearray(pixels), cairo.FORMAT_RGB24, width, h)
			
			ctx.set_source_surface(image, 0, 0)
			ctx.paint()		
		else:
			return NotImplemented
	
	def poke_image(self, view, document, ctx, box, px, py):
		if self.is_text_document(document):
			return []
		elif self.is_binary_document(document):
			return []
		else:
			return NotImplemented
	
	def image_dimensions(self, view, document):
		"Return text dimensions."
		
		if self.is_text_document(document):
			surface = cairo.RecordingSurface(cairo.Content.COLOR, None)
			ctx = cairo.Context(surface)
			ctx.select_font_face(self.__text_font)
			ctx.set_font_size(self.__text_size)
			extents = ctx.text_extents(document)
			return extents.width, self.__text_size + self.__text_spacing
		elif self.is_binary_document(document):
			s = len(document) * 8
			w = ceil(sqrt(s))
			h = ceil(s / w)
			return w, h
		else:
			return NotImplemented
	
	def image_height_for_width(self, view, document, width):
		if self.is_text_document(document):
			surface = cairo.RecordingSurface(cairo.Content.COLOR, None)
			ctx = cairo.Context(surface)
			ctx.select_font_face(self.__text_font)
			ctx.set_font_size(self.__text_size)
			
			lines = 0
			line = []
			offset = 0
			for word in re_split(r'[\r\n\t ]+', document):
				extents = ctx.text_extents(word)
				offset += extents.x_advance + 3.4
				if offset > width:
					if line:
						lines += 1
					line.clear()
					line.append(word)
					offset = extents.x_advance
					if offset > width:
						lines += 1
						line.clear()
						offset = 0
				else:
					line.append(word)
			if line:
				lines += 1
			
			return lines * (self.__text_size + self.__text_spacing)
		
		elif self.is_binary_document(document):
			s = len(document) * 8
			h = ceil(s / width)
			return h
		
		else:
			return NotImplemented
	
	def image_width_for_height(self, view, document, height):
		if self.is_text_document(document):
			return NotImplemented
		
		elif self.is_binary_document(document):
			s = len(document) * 8
			w = ceil(s / height)
			return w
		
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	print("plain format")
	
	model = PlainFormat()
	
	a = model.create_document(b'hello,void', 'text/plain')
	assert model.save_document(a).getvalue() == b'hello,void'
	
	b = model.create_document(b'hello,void', 'application/octet-stream')
	assert model.save_document(b).getvalue() == b'hello,void'

