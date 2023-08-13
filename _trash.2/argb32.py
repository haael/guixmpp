#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'ImageModel',


from io import BytesIO
import cairo


class ImageModel:
	def create_document(self, data, mime):
		if mime == 'image/x-argb32':
			w = int.from_bytes(data[0:4], byteorder='little', signed=False)
			h = int.from_bytes(data[4:8], byteorder='little', signed=False)
			assert len(data) == 4 * w * h + 8
			m = memoryview(bytearray(data))[8 : 4 * w * h + 8]
			return cairo.ImageSurface.create_for_data(m, cairo.Format.ARGB32, w, h)
		else:
			return NotImplemented
	
	def save_document(self, document, fileobj=None):
		if self.is_raster_image_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			fileobj.write(document.get_width().to_bytes(length=4, byteorder='little', signed=False))
			fileobj.write(document.get_height().to_bytes(length=4, byteorder='little', signed=False))
			fileobj.write(document.get_data())
			return fileobj
		elif self.is_vector_image_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			device = cairo.ScriptDevice(fileobj)
			device.from_recording_surface(document)
			device.finish()
			return fileobj
		else:
			return NotImplemented
	
	def is_raster_image_document(self, document):
		return isinstance(document, cairo.ImageSurface)
	
	def is_vector_image_document(self, document):
		return isinstance(document, cairo.RecordingSurface)
