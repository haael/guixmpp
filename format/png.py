#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PNGFormat',


import cairo
from io import BytesIO


class PNGFormat:
	def create_document(self, data, mime_type):
		if mime_type == 'image/png':
			return cairo.ImageSurface.create_from_png(BytesIO(data))
		else:
			return NotImplemented


if __name__ == '__main__':
	from pathlib import Path
	
	model = PNGFormat()
	for filepath in Path('gfx').iterdir():
		if filepath.suffix == '.png':
			mime_type = 'image/png'
		elif filepath.suffix in ['.jpg', '.jpeg']:
			mime_type = 'image/jpeg'
		elif filepath.suffix == '.css':
			mime_type = 'text/css'
		else:
			continue
		document = model.create_document(filepath.read_bytes(), mime_type)
		print(filepath, type(document))
