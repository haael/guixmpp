#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'HTMLFormat', 'HTMLDocument'


if __name__ == '__main__':
	import sys
	del sys.path[0]


from io import BytesIO
from litehtml import litehtml, litehtmlpy


class HTMLFormat:
	#xmlns_xml = 'http://www.w3.org/XML/1998/namespace'
	#xmlns_xlink = 'http://www.w3.org/1999/xlink'
	
	def create_document(self, data:bytes, mime:str):
		if mime == 'text/html' or mime == 'application/xhtml+xml':
			container = DocumentContainer()
			document = litehtmlpy.fromString(container, data, None, None)
			return document
		else:
			return NotImplemented
	
	#def save_document(self, document, fileobj=None):
	#	if self.is_xml_document(document):
	#		if fileobj == None:
	#			fileobj = BytesIO()
	#		fileobj.write(tostring(document))
	#		return fileobj
	#	else:
	#		return NotImplemented
	
	def is_html_document(self, document):
		return isinstance(document, litehtmlpy.document)
	
	#def get_document_fragment(self, document, href):
	#	if not self.is_xml_document(document):
	#		return NotImplemented
	#	fragment = document.findall(f".//*[@id='{href}']") # TODO: errors, escape
	#	#print("fragment:", fragment[0].tag, fragment[0].attrib)
	#	if fragment:
	#		return XMLDocument(fragment[0])
	#	else:
	#		raise IndexError("Fragment not found")
	
	def scan_document_links(self, document):
		#if self.is_xml_document(document):
		#	return document.scan_stylesheets()
		#else:
		#	return NotImplemented
		return NotImplemented
	
	#def are_nodes_ordered(self, ancestor, descendant):
	#	if not (hasattr(ancestor, 'getparent') and hasattr(descendant, 'getparent')):
	#		return NotImplemented
	#	
	#	parent = descendant
	#	while parent != None:
	#		if parent == ancestor:
	#			return True
	#		parent = parent.getparent()
	#	
	#	return False
	
	def image_dimensions(self, view, document):
		"Return the HTML dimensions, that might depend on the view state."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		size = int(210 * 3.96 * 96 / 72)
		document.render(size, litehtmlpy.render_all)
		
		try:
			html_width = document.width()
		except KeyError:
			html_width = self.get_viewport_width(view)
		
		try:
			html_height = document.height()
		except KeyError:
			html_height = self.get_viewport_height(view)
		
		return html_width, html_height
	
	def draw_image(self, view, document, ctx, box):
		"Perform HTML rendering."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		print("draw html")
		size = int(210 * 3.96 * 96 / 72)
		document.render(size, litehtmlpy.render_all)
		clip = litehtmlpy.position(0, 0, document.width(), document.height())
		document.draw(ctx, 0, 0, clip)
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_html_document(document):
			return NotImplemented
		
		print("poke html")


class DocumentContainer(litehtml.document_container):
	def delete_font(self):
		pass


#class HTMLDocument:
#	def __init__(self, data):
#		self.container = DocumentContainer()
#		self.document = litehtmlpy.fromString(self.container, data, None, None)
	
#	def render(self, ctx):
#		self.document.render(self.container.size[0], litehtmlpy.render_all)
#		clip = litehtmlpy.position(0, 0, self.document.width(), self.document.height())
#		self.document.draw(0, 0, 0, clip)



if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("html format")
	
	model = HTMLFormat()
	a = model.create_document(b'<html><head><title>title</title></head><body>body</body></html>', 'text/html')
	assert model.is_html_document(a)
	
	for example in Path('examples/docs').iterdir():
		if not example.is_dir(): continue
		for htmlfile in example.iterdir():
			if htmlfile.suffix not in ('.htm', '.html'): continue
			document = model.create_document(htmlfile.read_bytes(), 'text/html')
			assert model.is_html_document(document)
	
	#print(list(model.scan_xml_stylesheets(a)))
	#print(model.save_document(a).getvalue())

