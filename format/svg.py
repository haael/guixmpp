#!/usr/bin/python3


__all__ = 'SVGFormat',


class SVGFormat:
	"Supports creating and rendering SVG images, also supports CSS."
	
	xmlns_svg = 'http://www.w3.org/2000/svg'
	xmlns_sodipodi = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
	xmlns_inkscape = 'http://www.inkscape.org/namespaces/inkscape'
	
	def create_document(self, data, mime_type):
		if mime_type == 'image/svg+xml' or mime_type == 'image/svg':
			document = self.create_xml_document(data)
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

