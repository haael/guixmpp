#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'NullFormat',


class NullFormat:
	def create_document(self, data, mime_type):
		if mime_type in 'application/x-null':
			return None
		else:
			return NotImplemented
	
	def destroy_document(self, document):
		if not self.is_null_document(document):
			return NotImplemented
	
	def is_null_document(self, document):
		return document is None
	
	def scan_document_links(self, document):
		if self.is_null_document(document):
			return []
		else:
			return NotImplemented


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("null format")
	
	model = NullFormat()
	assert model.create_document(b"", 'application/x-null') is None

