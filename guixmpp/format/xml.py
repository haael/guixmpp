#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'XMLFormat', 'XMLDocument', 'XMLElement'


if __name__ == '__main__':
	import sys
	del sys.path[0] # needs to be removed because this module is called "xml"


from io import BytesIO
from lxml.etree import _ElementTree, ElementBase, fromstring as xml_frombytes, tostring as xml_tounicode, XMLParser, ElementDefaultClassLookup, ProcessingInstruction
from lxml.html import document_fromstring as html_frombytes, tostring as html_tobytes
from collections import defaultdict


class XMLElement(ElementBase):
	PR_INSTR_SHADOW_PARENT = 'x-haael-shadowparent'
	__shadow_parents = defaultdict(lambda: [None, 0])
	
	def _init(self):
		try:
			del self.__shadow_parent
		except AttributeError:
			pass
		
		for p in list(self):
			if p.tag == ProcessingInstruction and p.target == self.PR_INSTR_SHADOW_PARENT:
				self.__shadow_parent = self.__shadow_parents[p.text][0]
	
	def set_shadow_parent(self, parent):
		if parent:
			self.set_shadow_parent(None)
			
			self.__shadow_parent = parent
			parent_id = id(parent)
			self.__shadow_parents[parent_id][0] = parent
			self.__shadow_parents[parent_id][1] += 1
		
		else:
			try:
				parent_id = id(self.__shadow_parent)
				del self.__shadow_parent
			except AttributeError:
				pass
			else:
				self.__shadow_parents[parent_id][1] -= 1
				if self.__shadow_parents[parent_id][1] <= 0:
					del self.__shadow_parents[parent_id]
				
				for p in list(self):
					if p.tag == ProcessingInstruction and p.target == self.PR_INSTR_SHADOW_PARENT and p.text == parent_id:
						self.remove(p)
	
	def get_shadow_parent(self):
		try:
			return self.__shadow_parent
		except AttributeError:
			return self.getparent()
	
	def create_document(self):
		return self.XMLDocument(self.__copy__())
	
	def getroottree(self):
		return self.XMLDocument(super().getroottree().getroot())


class XMLDocument(_ElementTree):
	def __init__(self, element):
		self._setroot(element)
	
	def __eq__(self, other):
		if hasattr(other, 'getroot'):
			return self.getroot() == other.getroot()
		else:
			return False
	
	def __hash__(self):
		return hash(self.getroot())
	
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
		return xml_tounicode(self) # FIXME
	
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


class XMLFormat:
	xmlns_xml = 'http://www.w3.org/XML/1998/namespace'
	xmlns_xlink = 'http://www.w3.org/1999/xlink'
	
	def __init__(self, *args, XMLDocument=XMLDocument, XMLElement=XMLElement, **kwargs):
		self.XMLDocument = XMLDocument
		XMLElement.XMLDocument = XMLDocument
		self.XMLElement = XMLElement
		
		self.xml_parser = XMLParser()
		self.xml_parser.set_element_class_lookup(ElementDefaultClassLookup(element=XMLElement))
	
	def xml_frombytes(self, s):
		return xml_frombytes(s, self.xml_parser)
	
	def html_frombytes(self, s):
		return html_frombytes(s)
	
	def create_document(self, data:bytes, mime:str):
		if mime == 'text/xml' or mime == 'application/xml' or mime.endswith('+xml'):
			document = self.XMLDocument(self.xml_frombytes(data))
			return document
		elif mime == 'text/sgml' or mime == 'application/sgml':
			sgml_text = data
			sgml_doc = self.html_frombytes(sgml_text)
			xml_text = html_tobytes(sgml_doc, encoding='utf-8', method='xml')
			document = self.create_document(xml_text, 'application/xml')
			return document
		else:
			return NotImplemented
	
	def destroy_document(self, document):
		if not self.is_xml_document(document):
			return NotImplemented
	
	def save_document(self, document, fileobj=None):
		if self.is_xml_document(document):
			if fileobj == None:
				fileobj = BytesIO()
			fileobj.write(xml_tounicode(document))
			return fileobj
		else:
			return NotImplemented
	
	def is_xml_document(self, document):
		return isinstance(document, self.XMLDocument)
	
	def get_document_fragment(self, document, href):
		if not self.is_xml_document(document):
			return NotImplemented
		fragment = document.findall(f".//*[@id='{href}']") # TODO: errors, escape
		#print("fragment:", fragment[0].tag, fragment[0].attrib)
		if fragment:
			return fragment[0].create_document()
		else:
			raise IndexError(f"Fragment not found: {href}")
	
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


if __name__ == '__main__':
	from pathlib import Path
	
	print("xml format")
	
	model = XMLFormat()
	a = model.create_document(b'''<?xml version="1.0" encoding="utf-8"?>
<?xml-stylesheet href="data:text/css,a{display:block;}"?>
<?xml-stylesheet href="data:text/css,a b{display:inline;}"?>
<a>
 <b b1="1" b2="2"></b>
 <c c1="1" c2="2"></c>
 <d d1="1" d2="2"></d>
 <e e1="1" e2="2"></e>
</a>
''', 'application/xml')
	assert model.is_xml_document(a)
	
	b = model.create_document(b'''
<!DOCTYPE a>
<a>
 <b b1 b2=b>
 <c c1 c2=c>
 <d d1 d2=d>
 <e e1 e2=e>
</a>
''', 'application/sgml')
	assert model.is_xml_document(b)

	c = model.create_document(b'''
<!DOCTYPE html>
<html>
 <head>
  <meta key="a" value="b">
  <meta key="a" value="b">
 </head>
 <body>
  <ul>
   <li>1
   <li>2
   <li>3
  </ul>
 </body>
</html>
''', 'application/sgml')
	assert model.is_xml_document(c)
	
	#print(a.to_bytes())
	#print(b.to_bytes())
	#print(c.to_bytes())
	#d = a.getroot()[2]
	#e = a.getroot()[3]
	
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		for xmlfile in example.iterdir():
			if xmlfile.suffix not in ('.xml', '.svg'): continue
			document = model.create_document(xmlfile.read_bytes(), 'application/xml')
			assert model.is_xml_document(document)
	
	#print(list(model.scan_xml_stylesheets(a)))
	#print(model.save_document(a).getvalue())

