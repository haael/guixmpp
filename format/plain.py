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


if __debug__ and __name__ == '__main__':
	print("plain format")
	
	model = PlainFormat()
	
	a = model.create_document(b'hello,void', 'text/plain')
	assert model.save_document(a).getvalue() == b'hello,void'
	
	b = model.create_document(b'hello,void', 'application/octet-stream')
	assert model.save_document(b).getvalue() == b'hello,void'

