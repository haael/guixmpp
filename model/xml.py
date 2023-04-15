#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'XMLModel',


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "xml"


from io import BytesIO
from lxml.etree import ElementTree, fromstring, tostring


class XMLModel:
	xmlns_xml = 'http://www.w3.org/XML/1998/namespace'
	xmlns_xlink = 'http://www.w3.org/1999/xlink'
	
	def create_document(self, data:bytes, mime:str):
		if mime == 'text/xml' or mime == 'application/xml':
			document = ElementTree()
			document._setroot(fromstring(data))		
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
	
	def traverse_xml(self, node, param, pre_function, post_function):
		if pre_function != None:
			node, param = pre_function(node, param)
		
		children = []
		for child in node:
			child = self.traverse_xml(child, param, pre_function, post_function)
			children.append(child)
		
		if post_function != None:
			node = post_function(node, children)
		return node
	
	def scan_xml_stylesheets(self, document):
		el = document.getroot().getprevious()
		links = []
		while el != None:
			try:
				if el.target == 'xml-stylesheet':
					links.append(el.attrib['href'])
			except (AttributeError, KeyError):
				pass
			el = el.getprevious()
		return reversed(links)
	
	def is_xml_document(self, document):
		if not hasattr(document, 'getroot'):
			return False
		try:
			return document.docinfo.xml_version == '1.0'
		except AttributeError:
			return False


if __debug__ and __name__ == '__main__':
	print("xml model")
	
	model = XMLModel()
	a = model.create_document(b'<?xml-stylesheet href="data:text/css,a{display:block;}"?><?xml-stylesheet href="data:text/css,a b{display:inline;}"?><a><b/><b><c/></b></a>', 'application/xml')
	assert model.is_xml_document(a)
	print(list(model.xml_stylesheets(a)))
	print(model.save_document(a).getvalue())

