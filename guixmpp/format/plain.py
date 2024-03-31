#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PlainFormat',


from io import BytesIO
from math import ceil
import cairo
from re import split as re_split


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
			d = 11
			xd = ceil(width / d)
			if xd % 2 == 0:
				xd += 1
			yd = ceil(height / d)
			if yd % 2 == 0:
				yd += 1
			
			ctx.set_source_rgba(0.9, 0.4, 0.9, 0.5)
			for x in range(xd):
				for y in range(yd):
					if (x % 2) or (y % 2): continue
					ctx.rectangle(left + x * width / xd, top + y * height / yd, width / xd, height / yd)
					ctx.fill()
		
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
		
		if not self.is_text_document(document) and not self.is_binary_document(document):
			return NotImplemented
		
		if self.is_binary_document(document):
			document = document.decode('utf-8')
		
		surface = cairo.RecordingSurface(cairo.Content.COLOR, None)
		ctx = cairo.Context(surface)
		ctx.select_font_face(self.__text_font)
		ctx.set_font_size(self.__text_size)
		extents = ctx.text_extents(document)
		
		return extents.width, self.__text_size + self.__text_spacing
	
	def image_height_for_width(self, view, document, width):
		if not self.is_text_document(document) and not self.is_binary_document(document):
			return NotImplemented
		
		if self.is_binary_document(document):
			document = document.decode('utf-8')
		
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


if __debug__ and __name__ == '__main__':
	print("plain format")
	
	model = PlainFormat()
	
	a = model.create_document(b'hello,void', 'text/plain')
	assert model.save_document(a).getvalue() == b'hello,void'
	
	b = model.create_document(b'hello,void', 'application/octet-stream')
	assert model.save_document(b).getvalue() == b'hello,void'

