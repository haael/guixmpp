#!/usr/bin/python3


__all__ = 'SVGFormat',


class SVGFormat:
	"Supports creating and rendering SVG images, also supports CSS."
	
	xmlns_svg = 'http://www.w3.org/2000/svg'
	#xmlns_sodipodi = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
	#xmlns_inkscape = 'http://www.inkscape.org/namespaces/inkscape'
	
	def create_document(self, data, mime_type):
		if mime_type == 'image/svg+xml' or mime_type == 'image/svg':
			document = self.create_document(data, 'application/xml')
			if document.getroot().tag == f'{{{self.xmlns_svg}}}svg':
				return document
			else:
				raise ValueError("Not an SVG document.")
		else:
			return NotImplemented
	
	def is_svg_document(self, document):
		return self.is_xml_document(document) and document.getroot().tag == f'{{{self.xmlns_svg}}}svg'
	
	def scan_document_links(self, document):
		if self.is_svg_document(document):
			return self.scan_xml_stylesheets(document)
		else:
			return NotImplemented
	
	def element_tabindex(self, document, element):
		if self.is_svg_document(document):
			return None
		else:
			return NotImplemented
	

if __debug__ and __name__ == '__main__':
	from pathlib import Path
	from format.xml import XMLFormat
	
	print("svg format")	
	
	class Model(SVGFormat, XMLFormat):
		def create_document(self, data, mime_type):
			if mime_type == 'application/xml':
				return XMLFormat.create_document(self, data, mime_type)
			else:
				return SVGFormat.create_document(self, data, mime_type)
	
	model = Model()
	for filepath in Path('gfx').iterdir():
		if filepath.suffix != '.svg': continue
		document = model.create_document(filepath.read_bytes(), 'image/svg')
		assert model.is_svg_document(document)
