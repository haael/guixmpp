#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'PlainFormat',


from io import BytesIO


class PlainFormat:
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
	
	'''
	def draw_image(self, view, document, ctx, box):
		"Image placeholder for broken links."
		
		if self.is_text_document(document):
			left, top, width, height = box		
			d = 11
			xd = ceil(width / d)
			if xd % 2 == 0:
				xd += 1
			yd = ceil(height / d)
			if yd % 2 == 0:
				yd += 1
			
			ctx.set_source_rgba(0.5, 0.5, 1, 0.5)
			for x in range(xd):
				for y in range(yd):
					if (x % 2) or (y % 2): continue
					ctx.rectangle(left + x * width / xd, top + y * height / yd, width / xd, height / yd)
					ctx.fill()
			
			return defaultdict(list)
		
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
			
			return defaultdict(list)
		
		else:
			return NotImplemented
	'''



if __debug__ and __name__ == '__main__':
	print("plain format")
	
	model = PlainFormat()
	
	a = model.create_document(b'hello,void', 'text/plain')
	assert model.save_document(a).getvalue() == b'hello,void'
	
	b = model.create_document(b'hello,void', 'application/octet-stream')
	assert model.save_document(b).getvalue() == b'hello,void'

