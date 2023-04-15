#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'ImageFormat',


import gi
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')

from gi.repository import GdkPixbuf, GLib, Gdk


class ImageFormat:
	def create_document(self, data, mime_type):
		try:
			loader = GdkPixbuf.PixbufLoader.new_with_mime_type(mime_type)
		except GLib.Error:
			return NotImplemented
		else:
			loader.write(data)
			loader.close()
			return Gdk.cairo_surface_create_from_pixbuf(loader.get_pixbuf(), 0, None)


if __name__ == '__main__':
	from pathlib import Path
	
	model = ImageFormat()
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

