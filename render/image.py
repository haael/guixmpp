#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'ImageRender',


import cairo


class ImageRender:
	"Supports creating and rendering PNG images."
	
	def document_width(self, document, viewport_width, viewport_height):
		if self.is_image_document(document):
			return document.get_width()
		else:
			return NotImplemented
	
	def document_height(self, document, viewport_width, viewport_height):
		if self.is_image_document(document):
			return document.get_height()
		else:
			return NotImplemented
	
	def draw_document(self, document, ctx, box, vw, vh):
		if self.is_image_document(document):
			ctx.set_source_surface(document)
			ctx.scale(box[2] / self.document_width(document, vw, vh), box[3] / self.document_height(document, vw, vh))
			ctx.rectangle(*box)
			ctx.fill()
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	class PseudoContext:
		def __init__(self, name):
			self.__name = name
		
		def get_current_point(self):
			print(self.__name + '.get_current_point()')
			return 0, 0
		
		def get_line_width(self):
			print(self.__name + '.get_line_width()')
			return 1
		
		def copy_path(self):
			print(self.__name + '.copy_path()')
			return [(cairo.PATH_MOVE_TO, (0, 0))]
		
		def path_extents(self):
			print(self.__name + '.path_extents()')
			return 0, 0, 1, 1
		
		def set_dash(self, dashes, offset):
			print(self.__name + '.set_dash(', repr(dashes), ',', repr(offset), ')')
		
		def __getattr__(self, attr):
			return lambda *args: print(self.__name + '.' + attr + str(args))
	
	rnd = ImageRender()
	for filepath in Path('gfx').iterdir():
		if filepath.suffix.lower() != '.png': continue
		print()
		print(filepath)
		png = cairo.ImageSurface.create_from_png(BytesIO(filepath.read_bytes()))
		rnd.draw_document(png, PseudoContext(str(filepath)), (0, 0, rnd.document_width(png, 300, 200), rnd.document_height(png, 300, 200)), 300, 200)




