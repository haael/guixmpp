#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'XMLFormat', 'XMLDocument'


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "xml"


from io import BytesIO
from lxml.etree import _ElementTree, fromstring, tostring


class XMLFormat:
	#xmlns_xml = 'http://www.w3.org/XML/1998/namespace'
	#xmlns_xlink = 'http://www.w3.org/1999/xlink'
	
	def create_document(self, data:bytes, mime:str):
		if mime == 'text/xml' or mime == 'application/xml' or mime.endswith('+xml'):
			document = XMLDocument(fromstring(data))
			return document
		else:
			return NotImplemented
	
	def save_document(self, document, fileobj=None):
		if self.is_xml_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			fileobj.write(tostring(document))
			return fileobj
		else:
			return NotImplemented
	
	def is_xml_document(self, document):
		if not hasattr(document, 'getroot'):
			return False
		try:
			return document.docinfo.xml_version == '1.0'
		except AttributeError:
			return False
	
	def get_document_fragment(self, document, href):
		if not self.is_xml_document(document):
			return NotImplemented
		fragment = document.findall(f".//*[@id='{href}']") # TODO: errors, escape
		#print("fragment:", fragment[0].tag, fragment[0].attrib)
		if fragment:
			return XMLDocument(fragment[0])
		else:
			raise IndexError("Fragment not found")
	
	def scan_document_links(self, document):
		if self.is_xml_document(document):
			return document.scan_stylesheets()
		else:
			return NotImplemented
	
	def are_nodes_ordered(self, ancestor, descendant):
		if not (hasattr(ancestor, 'getparent') and hasattr(descendant, 'getparent')):
			return NotImplemented
		
		parent = descendant
		while parent != None:
			if parent == ancestor:
				return True
			parent = parent.getparent()
		
		return False


class XMLDocument(_ElementTree):
	def __init__(self, element):
		self._setroot(element)
	
	def __eq__(self, other):
		if hasattr(other, 'getroot'):
			return self.getroot() == other.getroot()
		else:
			return False
	
	def __hash__(self):
		return hash(self.getroot().getroottree())
	
	def scan_stylesheets(self):
		el = self.getroot().getprevious()
		links = []
		while el != None:
			try:
				if el.target == 'xml-stylesheet':
					links.append(el.attrib['href'])
			except (AttributeError, KeyError):
				pass
			el = el.getprevious()
		return reversed(links)
	
	def to_bytes(self):
		return tostring(self)


if __debug__ and __name__ == '__main__':
	from pathlib import Path
	
	print("xml format")
	
	model = XMLFormat()
	a = model.create_document(b'<?xml-stylesheet href="data:text/css,a{display:block;}"?><?xml-stylesheet href="data:text/css,a b{display:inline;}"?><a><b/><b><c/></b></a>', 'application/xml')
	assert model.is_xml_document(a)
	
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		for xmlfile in example.iterdir():
			if xmlfile.suffix not in ('.xml', '.svg'): continue
			document = model.create_document(xmlfile.read_bytes(), 'application/xml')
			assert model.is_xml_document(document)
	
	#print(list(model.scan_xml_stylesheets(a)))
	#print(model.save_document(a).getvalue())

