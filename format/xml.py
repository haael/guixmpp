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
		return hash(self.getroottree())
	
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
	
	def getpath(self, node):
		if hasattr(node, 'path_override'):
			return node.path_override
		else:
			return super().getpath(node)
	
	def xpath(self, path):
		if path.startswith('§'):
			return [eval(path[1:], globals(), {'xpath':lambda _path: self.xpath(_path)[0]})]
		else:
			return super().xpath(path)


class OverlayElement:
	def __init__(self, parent, one, two, tag, add_attrib, del_attrib):
		if not isinstance(tag, str): raise ValueError
		#if one is None: raise ValueError
		if two is None: raise ValueError
		
		#if isinstance(one, OverlayElement): raise ValueError(f"Can not nest OverlayElement: {one.tag}")	
		#if isinstance(two, OverlayElement): raise ValueError(f"Can not nest OverlayElement: {two.tag}")	
		
		self.__one = one
		self.__two = two
		self.__parent = parent
		self.__tag = tag
		rt = XMLDocument(parent.getroottree().getroot())
		one_path = ("xpath(" + repr(rt.getpath(one)) + ")") if (one is not None) else None
		self.path_override = f'§OverlayElement(xpath({repr(rt.getpath(parent))}), {one_path}, xpath({repr(rt.getpath(two))}), {repr(tag)}, dict({repr(sorted(add_attrib.items()))}), {repr(sorted(del_attrib))})'
		self.__add_attrib = add_attrib
		self.__del_attrib = del_attrib
	
	def __repr__(self):
		return f"<OverlayElement {self.tag}>"
	
	def __eq__(self, other):
		try:
			#return self.__one == other.__one and self.__two == other.__two and self.__parent == other.__parent and self.__tag == other.__tag and self.__add_attrib == other.__add_attrib and self.__del_attrib == other.__del_attrib
			return self.tag == other.tag and self.attrib == other.attrib and self.getparent() == other.getparent()
		except AttributeError:
			return NotImplemented
	
	def __hash__(self):
		return hash((self.tag, tuple(sorted(self.attrib.items()))))
	
	def getparent(self):
		return self.__parent
	
	@property
	def tag(self):
		return self.__tag
	
	@property
	def attrib(self):
		if self.__one is not None:
			a = dict()
			a.update(self.__two.attrib)
			a.update(self.__one.attrib)
		else:
			a = dict(self.__two.attrib)
		
		a.update(self.__add_attrib)
		for attr in self.__del_attrib:
			try:
				del a[attr]
			except KeyError:
				pass
		
		return a
	
	def __getattr__(self, attr):
		if attr[0] != '_':
			return getattr(self.__two, attr)
		else:
			raise AttributeError(f"No attibute found in OverlayElement: {attr}")
	
	def __len__(self):
		return len(self.__two)
	
	def __getitem__(self, index):
		original = self.__two[index]
		if not isinstance(original.tag, str): # not element
			return original
		return self.__class__(self, None, original, original.tag, {}, [])
	
	def getroottree(self):
		return XMLDocument(self.__parent.getroottree().getroot())
	
	def orig_one(self):
		try:
			return self.__one.orig_one()
		except AttributeError:
			return self.__one if (self.__one is not None) else self.__two


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

