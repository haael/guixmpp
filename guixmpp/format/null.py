#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'NullFormat',


from math import ceil
from collections import defaultdict


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
	
	'''
	def draw_image(self, view, document, ctx, box):
		"Image placeholder for broken links."
		
		if not self.is_null_document(document):
			return NotImplemented
		
		left, top, width, height = box		
		d = 7
		xd = ceil(width / d)
		if xd % 2 == 0:
			xd += 1
		yd = ceil(height / d)
		if yd % 2 == 0:
			yd += 1
		
		ctx.set_source_rgba(1, 0, 0, 0.5)
		for x in range(xd):
			for y in range(yd):
				if (x % 2) or (y % 2): continue
				ctx.rectangle(left + x * width / xd, top + y * height / yd, width / xd, height / yd)
				ctx.fill()
		
		return defaultdict(list)
	'''


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("null format")
	
	model = NullFormat()
	assert model.create_document(b"", 'application/x-null') is None

