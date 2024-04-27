#!/usr/bin/python3
#-*- coding:utf-8 -*-


__all__ = 'HTMLRender',


if __name__ == '__main__':
	import sys
	del sys.path[0]


import re
import math
from enum import Enum
import cairo
from collections import defaultdict, namedtuple
from weakref import WeakKeyDictionary
from itertools import chain, starmap
from urllib.parse import quote as url_quote
from colorsys import hls_to_rgb

#import PIL.Image, PIL.ImageFilter

import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

if __name__ == '__main__':
	from guixmpp.format.xml import XMLFormat
	from guixmpp.format.css import CSSFormat
else:
	from ..format.xml import XMLFormat
	from ..format.css import CSSFormat


class BoxTree:
	def __init__(self, node, pseudoelement, content):
		self.node = node
		self.pseudoelement = pseudoelement
		self.content = content
		self.style = {}
	
	def debug_print(self, level=0):
		if isinstance(self.content, str):
			print(level * " ", repr(self.content), self.style)
		else:
			print(level * " ", self.node.tag if hasattr(self.node, 'tag') else '-', self.style)
			for child in self.content:
				child.debug_print(level + 1)


class HTMLRender:
	xmlns_xml = XMLFormat.xmlns_xml
	xmlns_xlink = XMLFormat.xmlns_xlink
	
	xmlns_html = 'http://www.w3.org/1999/xhtml'
	xmlns_html2 = 'http://www.w3.org/2002/06/xhtml2'
	
	web_colors = CSSFormat.web_colors
	
	def __init__(self, *args, **kwargs):
		self.__css_matcher = WeakKeyDictionary()
	
	def create_document(self, data, mime_type):
		if mime_type == 'application/xhtml' or mime_type == 'application/xhtml+xml' or mime_type == 'text/html':
			if mime_type == 'text/html':
				document = self.create_document(data, 'text/x-html-tag-soup')
			else:
				document = self.create_document(data, 'application/xml')
			
			if document.getroot().tag == 'html': # document without namespace
				del document.getroot().attrib['xmlns'] # workaround: lxml sets xmlns twice
				document = self.create_document(document.to_bytes(), 'application/xml')
			
			if document.getroot().tag == 'html': # still without namespace
				document.getroot().attrib['xmlns'] = self.xmlns_html
				document = self.create_document(document.to_bytes(), 'application/xml')
			
			if self.is_html_document(document):
				return document
			else:
				raise ValueError("Not an HTML document.")
		else:
			return NotImplemented
	
	def is_html_document(self, document):
		if self.is_xml_document(document):
			return document.getroot().tag.startswith('{' + self.xmlns_html + '}') or document.getroot().tag.startswith('{' + self.xmlns_html2 + '}')
		else:
			try:
				return document.tag.startswith('{' + self.xmlns_html + '}') or document.tag.startswith('{' + self.xmlns_html2 + '}')
			except AttributeError:
				return False
	
	def __xmlns(self, document):
		try:
			return document.getroot().tag.split('}')[0][1:]
		except AttributeError:
			return document.tag.split('}')[0][1:]
	
	def scan_document_links(self, document):
		"Yield all links referenced by the HTML document, including `data:` links."
		
		if self.is_html_document(document):
			def links():
				yield 'chrome://html.css'
				yield from document.scan_stylesheets()
				yield from self.__xlink_hrefs(document)
				yield from self.__data_internal_links(self.__style_attrs(document))
				yield from self.__data_internal_links(self.__style_tags(document))
				#yield from self.__script_tags(document)
			return links()
		else:
			return NotImplemented
	
	def __xlink_hrefs(self, document):
		xmlns_html = self.__xmlns(document)
		for linkedtag in document.findall(f'.//*[@{{{self.xmlns_xlink}}}href]'):
			if linkedtag.tag == f'{{{self.xmlns_html}}}a' or linkedtag.tag.split('}')[0][1:] not in [self.xmlns_html, self.xmlns_html2]:
				continue
			href = linkedtag.attrib[f'{{{self.xmlns_xlink}}}href']
			yield href
		for linkedtag in document.findall(f'.//*[@href]'):
			if linkedtag.tag == f'{{{xmlns_html}}}a' or linkedtag.tag.split('}')[0][1:] not in [self.xmlns_html, self.xmlns_html2]:
				continue
			href = linkedtag.attrib['href']
			yield href
	
	def __data_internal_links(self, urls):
		"Recursively examine provided urls for internal urls they may reference."
		
		for url in urls:
			yield url
			if url.startswith('data:'):		
				yield from self.__data_internal_links(self.scan_document_links(self.get_document(url)))
	
	def __style_attrs(self, document):
		"Yield all style='...' attributes as 'data:' urls."
		
		if 'style' in document.getroot().attrib:
			style = '* {' + document.getroot().attrib['style'] + '}'
			yield 'data:text/css,' + url_quote(style)
		
		for styledtag in document.findall('.//*[@style]'):
			style = '* {' + styledtag.attrib['style'] + '}'
			yield 'data:text/css,' + url_quote(style)
	
	def __style_tags(self, document):
		"Yield all <style/> tags as 'data:' urls."
		
		xmlns_html = self.__xmlns(document)
		for styletag in document.findall(f'.//{{{xmlns_html}}}style'):
			try:
				mime = styletag.attrib['type'].lower()
			except KeyError:
				mime = 'text/css'
			style = styletag.text
			yield f'data:{mime},' + url_quote(style)
	
	def image_dimensions(self, view, document):
		"Return the SVG dimensions, that might depend on the view state."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		return self.get_viewport_width(view), self.get_viewport_height(view)
	
	def image_width_for_height(self, view, document, height):
		if not self.is_html_document(document):
			return NotImplemented
		w, h = self.image_dimensions(view, document)
		return w # TODO
	
	def image_height_for_width(self, view, document, width):
		if not self.is_html_document(document):
			return NotImplemented
		w, h = self.image_dimensions(view, document)
		return h # TODO
	
	def draw_image(self, view, document, ctx, box):
		"Perform HTML rendering."
		
		if not self.is_html_document(document):
			return NotImplemented
		
		xmlns_html = self.__xmlns(document)
		
		#from lxml.etree import tostring
		#print(type(document), tostring(document))
		
		if hasattr(document, 'getroot'): # render whole HTML document
			node = document.findall(f'.//{{{xmlns_html}}}body')[0] # FIXME
		else: # render one HTML tag
			node = document
			document = document.getroottree()
			#print("render html tag:", node, document)
		
		ctx.rectangle(*box)
		ctx.clip()
		
		ctx.set_source_rgb(0, 0, 0)
		ctx.set_line_width(1)
		ctx.select_font_face('serif')
		ctx.set_font_size(16)
		
		body = self.__create_box(view, document, ctx, node, None, xmlns_html)[0]
		
		body.style['x'] = 0
		body.style['y'] = 0
		
		root = BoxTree(None, None, [body])
		root.style['font-size'] = em_size = self.__get_attribute(view, document, node, None, 'font-size', 16)
		root.style['font-family'] = self.__get_attribute(view, document, node, None, 'font-family', 'serif')
		root.style['width'] = root.style['viewport-width'] = box[2]
		root.style['viewport-height'] = box[3]
		root.style['x'] = box[0]
		root.style['y'] = box[1]
		
		self.__position_box_inline(view, ctx, document, body, root, em_size)
		self.__position_box_block(view, ctx, document, body, root)
		root.debug_print()
		self.__render_box(view, ctx, document, body, root)
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_html_document(document):
			return NotImplemented
		
		xmlns_html = self.__xmlns(document)
		
		if hasattr(document, 'getroot'):
			node = document.findall(f'.//{{{xmlns_html}}}body')[0]
		else:
			document = document.getroottree().getroot().create_document()
			node = document.findall(f'.//{{{xmlns_html}}}body')[0]
		
		#return self.__render_tag(view, document, ctx, box, node, em_size, (px, py))
		return []
	
	def __create_box(self, view, document, ctx, node, pseudoelement, xmlns):
		display = self.__get_attribute(view, document, node, None, 'display', 'inline')
		if display == 'none':
			return []
		
		visibility = self.__get_attribute(view, document, node, None, 'visibility', 'visible')
		if visibility == 'collapse':
			return []
		
		result = []
		
		if pseudoelement is None:
			before = self.__get_attribute(view, document, node, 'before', 'content', None)
			if before is not None:
				result.extend(self.__create_box(view, document, ctx, node, 'before', xmlns))
			
			for child in chain([None], node):
				if child is None:
					text = node.text
				else:
					if isinstance(child.tag, str):
						result.extend(self.__create_box(view, document, ctx, child, None, xmlns))
					text = child.tail
				
				if text:
					result.extend(BoxTree(node, None, _word) for _word in (_rword.strip() for _rword in re.split(r'[\r\n\t ]', text)) if _word)
			
			after = self.__get_attribute(view, document, node, 'after', 'content', None)
			if after is not None:
				result.extend(self.__create_box(view, document, ctx, node, 'after', xmlns))
		
		else:
			text = self.__get_attribute(view, document, node, pseudoelement, 'content', None)
			if text[0] == text[-1] == '\"':
				result.append(BoxTree(node, pseudoelement, text[1:-1]))
			else:
				raise NotImplementedError
		
		if display != 'inline' or node.tag == f'{{{xmlns}}}body':
			box = BoxTree(node, pseudoelement, result)
			result = [box]
		
		return result
	
	def __position_box_inline(self, view, ctx, document, box, parent, em_size):
		node = box.node
		pseudoelement = box.pseudoelement
		
		parent_width = parent.style['width']
		font_size = em_size
		
		if node is not None:
			font_size_attr = self.__get_attribute(view, document, node, pseudoelement, 'font-size', None)
			if font_size_attr:
				try:
					float(font_size_attr) # font size can't be a unit-less number
				except ValueError:
					box.style['font-size'] = font_size = self.units(view, font_size_attr, em_size=em_size)
			
			font_family = self.__get_attribute(view, document, node, pseudoelement, 'font-family', None)
			if font_family:
				box.style['font-family'] = font_family
		
		if isinstance(box.content, str):
			line_height_attr = self.__get_attribute(view, document, node, pseudoelement, 'line-height', '1.25')
			try:
				line_height = float(line_height_attr) * font_size
			except (TypeError, ValueError):
				line_height = self.units(view, line_height_attr, percentage=font_size, em_size=font_size)
			
			word_spacing = self.units(view, self.__get_attribute(view, document, node, pseudoelement, 'word-spacing', '0.25em'), em_size=font_size)
			
			if font_family:
				ctx.select_font_face(font_family)
			if font_size:
				ctx.set_font_size(font_size)
			extents = ctx.text_extents(box.content)
			
			box.style.update({'line-height':line_height, 'word-spacing':word_spacing, 'width':extents.width, 'height':extents.height, 'x-advance':extents.x_advance})
		
		else:
			width_attr = self.__get_attribute(view, document, node, pseudoelement, 'width', 'auto')
			if width_attr == 'auto':
				width = parent_width
			else:
				width = self.units(view, width_attr, percentage=parent_width, em_size=font_size)
			
			box.style['width'] = width
			
			x = 0
			y = 0
			lh = 0
			fh = 0
			line = []
			for child in box.content:
				self.__position_box_inline(view, ctx, document, child, box, em_size)
				
				assert 'x-advance' in child.style or 'height' in child.style
				
				if 'x-advance' in child.style:
					if x + child.style['x-advance'] + child.style['word-spacing'] >= width:
						x = 0
						for lchild in line:
							lchild.style['y'] = y + fh
						y += lh
						lh = 0
						fh = 0
						line.clear()
					line.append(child)
					child.style['x'] = x
					x += child.style['x-advance'] + child.style['word-spacing']
					lh = max(lh, child.style['line-height'])
					fh = max(fh, child.style['font-size'] if 'font-size' in child.style else font_size)
				
				else:
					for lchild in line:
						lchild.style['y'] = y + fh
					y += lh
					child.style['x'] = 0
					child.style['y'] = y
					lh = 0
					fh = 0
					line.clear()
					x = 0
					y += child.style['height']
			
			for lchild in line:
				lchild.style['y'] = y + fh
			line.clear()
			y += lh
			
			box.style['height'] = y
	
	def __position_box_block(self, view, ctx, document, box, parent):
		node = box.node
		pseudoelement = box.pseudoelement
		
		box.style['x'] += parent.style['x']
		box.style['y'] += parent.style['y']
		
		#box.style['font-face'] = self.__get_attribute(view, document, node, None, 'font-face', 16)
		#box.style['font-size'] = self.__get_attribute(view, document, node, None, 'font-size', 16)
		
		if not isinstance(box.content, str):
			for child in box.content:
				self.__position_box_block(view, ctx, document, child, box)
	
	def __render_box(self, view, ctx, document, box, parent):
		node = box.node
		pseudoelement = box.pseudoelement
		
		if isinstance(box.content, str):
			x = box.style['x']
			y = box.style['y']
			ctx.move_to(x, y)
			
			try:
				font_size = box.style['font-size']
			except KeyError:
				pass
			else:
				ctx.set_font_size(font_size)
			
			try:
				font_face = box.style['font-face']
			except KeyError:
				pass
			else:
				ctx.set_font_face(font_face)
			
			ctx.show_text(box.content)
		else:
			for child in box.content:
				ctx.save()
				self.__render_box(view, ctx, document, child, box)
				ctx.restore()
	
	def __get_attribute(self, view, document, node, pseudoelement, attr, default):
		value = self.__search_attribute(view, document, node, pseudoelement, attr)
		if value is None:
			return default
		elif value == 'initial':
			return default
		else:
			return value
	
	def __media_test(self, view, media):
		return False
	
	def __pseudoelement_test(self, view, pelem):
		return False
	
	def __get_pseudoclasses(self, view, node):
		#pseudoclasses = set()
		#if hasattr(self, 'get_pointed'):
		#	pointed = self.get_pointed(view)
		#	if pointed is not None and self.are_nodes_ordered(node, pointed):
		#		pseudoclasses.add('hover')
		#return pseudoclasses
		return []
	
	def __get_classes(self, node):
		if 'class' in node.attrib:
			return frozenset(node.attrib['class'].split(' '))
		else:
			return []
	
	def __get_id(self, node):
		if 'id' in node.attrib:
			return node.attrib['id']
		else:
			return None
	
	def __search_attribute(self, view, document, node, pseudoelement, attr):
		xmlns_html = self.__xmlns(document)
		
		try:
			return view.__attr_cache[node, pseudoelement][attr]
		except KeyError:
			pass
		except AttributeError:
			view.__attr_cache = defaultdict(dict)
		
		if pseudoelement is None:
			"inline style='...' attribute"
			try:
				style = node.attrib['style']
			except (KeyError, AttributeError):
				pass
			else:
				css = self.get_document('data:text/css,' + url_quote('* {' + style + '}'))
				if self.is_css_document(css):
					if css not in self.__css_matcher:
						self.__css_matcher[css] = self.create_css_matcher(css, None, self.__get_id, None, None, None, node.tag.split('}')[1:] if node.tag[0] == '}' else '')
					css_attrs = self.__css_matcher[css](node)
					if attr in css_attrs:
						view.__attr_cache[node, pseudoelement][attr] = css_attrs[attr][0]
						return css_attrs[attr][0]
		
		"regular stylesheet (<style/> tag or external)"
		try:
			stylesheets = document.__stylesheets
		except AttributeError:
			stylesheets = list(self.__stylesheets(document))
			document.__stylesheets = stylesheets
		
		css_value = None
		css_priority = None
		
		for stylesheet in stylesheets:
			if stylesheet not in self.__css_matcher:
				self.__css_matcher[stylesheet] = self.create_css_matcher(stylesheet, (lambda _media: self.__media_test(view, _media)), self.__get_id, self.__get_classes, (lambda _node: self.__get_pseudoclasses(view, _node)), None, self.__xmlns(document))
			css_attrs = self.__css_matcher[stylesheet](node)
			
			#css_attrs = stylesheet.match_element(document, node, (lambda _media: self.__media_test(view, _media)), self.__get_id, self.__get_classes, (lambda _node: self.__get_pseudoclasses(view, _node)), self.__pseudoelement_test)
			if attr in css_attrs:
				value, priority = css_attrs[attr]
				if css_priority == None or priority >= css_priority:
					css_value = value
					css_priority = priority
		
		if css_value is not None:
			view.__attr_cache[node, pseudoelement][attr] = css_value
			return css_value
		
		parent = node.getparent()
		if parent is not None:
			result = self.__search_attribute(view, document, parent, None, attr)
			view.__attr_cache[node, pseudoelement][attr] = result
			return result
		else:
			return None
	
	def __stylesheets(self, document):
		myurl = self.get_document_url(document)
		
		doc = self.get_document('chrome://html.css')
		if self.is_css_document(doc):
			yield doc
		
		for link in document.scan_stylesheets():
			absurl = self.resolve_url(link, myurl)
			doc = self.get_document(absurl)
			if self.is_css_document(doc):
				yield doc
		
		for link in self.__data_internal_links(self.__style_tags(document)):
			absurl = self.resolve_url(link, myurl)
			doc = self.get_document(absurl)
			if self.is_css_document(doc):
				yield doc


if __debug__ and __name__ == '__main__':
	from pycallgraph2 import PyCallGraph
	from pycallgraph2.output.graphviz import GraphvizOutput
	
	from pathlib import Path
	from urllib.parse import unquote as url_unquote
	
	from guixmpp.format.xml import XMLFormat, XMLDocument
	from guixmpp.format.css import CSSFormat, CSSDocument
	from guixmpp.format.null import NullFormat
	from guixmpp.download.data import DataDownload
	from guixmpp.download.chrome import ChromeDownload
	
	print("html render")
	
	class PseudoContext:
		def __init__(self, name):
			self.__name = name
			self.print_out = False
			self.balance = 0
		
		def save(self):
			if self.print_out: print(self.__name + '.save()')
			self.balance += 1
		
		def restore(self):
			if self.print_out: print(self.__name + '.restore()')
			self.balance -= 1
		
		def get_current_point(self):
			if self.print_out: print(self.__name + '.get_current_point()')
			return 0, 0
		
		def get_line_width(self):
			if self.print_out: print(self.__name + '.get_line_width()')
			return 1
		
		def copy_path(self):
			if self.print_out: print(self.__name + '.copy_path()')
			return [(cairo.PATH_MOVE_TO, (0, 0))]
		
		def path_extents(self):
			if self.print_out: print(self.__name + '.path_extents()')
			return 0, 0, 1, 1
		
		def text_extents(self, txt):
			if self.print_out: print(f'{self.__name}.text_extents("{txt}")')
			#return cairo.Rectangle(0, 0, len(txt), 1)
			return cairo.TextExtents(0, 0, len(txt), 12, len(txt), 0)
		
		def set_dash(self, dashes, offset):
			if self.print_out: print(f'{self.__name}.set_dash({repr(dashes)}, {repr(offset)})')
			pass
		
		def device_to_user(self, x, y):
			if self.print_out: print(f'{self.__name}.device_to_user({x}, {y})')
			return x, y
		
		def __getattr__(self, attr):
			if self.print_out: return lambda *args: print(self.__name + '.' + attr + str(args))
			return lambda *args: None
	
	class HTMLRenderModel(HTMLRender, CSSFormat, XMLFormat, DataDownload, ChromeDownload, NullFormat):
		def __init__(self):
			HTMLRender.__init__(self)
			CSSFormat.__init__(self)
			XMLFormat.__init__(self)
			DataDownload.__init__(self)
			ChromeDownload.__init__(self)
			NullFormat.__init__(self)
		
		def scan_document_links(self, document):
			if HTMLRender.is_html_document(self, document):
				return HTMLRender.scan_document_links(self, document)
			elif CSSFormat.is_css_document(self, document):
				return CSSFormat.scan_document_links(self, document)
			elif XMLFormat.is_xml_document(self, document):
				return XMLFormat.scan_document_links(self, document)
			elif NullFormat.is_null_document(self, document):
				return NullFormat.scan_document_links(self, document)
			else:
				raise NotImplementedError(f"Could not scan links in unsupported document type: {type(document)}")
		
		def create_document(self, data, mime_type):
			if mime_type == 'application/xml' or mime_type == 'text/x-html-tag-soup':
				return XMLFormat.create_document(self, data, mime_type)
			elif mime_type == 'text/css':
				return CSSFormat.create_document(self, data, mime_type)
			elif mime_type == 'text/html' or mime_type == 'application/xhtml+xml':
				return HTMLRender.create_document(self, data, mime_type)
			else:
				raise NotImplementedError("Could not create unsupported document type.")
		
		def resolve_url(self, rel_url, base_url):
			return rel_url
		
		def emit_warning(self, view, message, target):
			print(message)
		
		def is_html_document(self, document):
			return hasattr(document, 'getroot')
		
		def get_document_url(self, document):
			return ''
		
		def get_document(self, url):
			if url.startswith('#'):
				return XMLDocument(self.tree.findall(f".//*[@id='{url[1:]}']")[0])
			elif url.startswith('data:text/css'):
				return CSSDocument(url_unquote(url[14:]).encode('utf-8'))
			elif url == 'chrome://html.css':
				print("global css")
				return CSSDocument(Path('chrome/html.css').read_bytes())
			return None
			#raise NotImplementedError("Could not fetch unsupported url scheme: " + url)
		
		def draw_image(self, view, document, ctx, box):
			r = super().draw_image(view, document, ctx, box)
			if r is NotImplemented:
				return defaultdict(list)
			return r
		
		def get_dpi(self, view):
			return 96
		
		def get_pointed(self, view):
			return None
	
	class PseudoView:
		def __init__(self):
			pass
	
	#nn = 0
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		
		for filepath in example.iterdir():
			if filepath.suffix not in ('.html', '.xhtml'): continue
			if filepath.name != 'simple.html': continue
			print(filepath)
			#if filepath.name != 'animated-text-fine-cravings.svg': continue
			#nn += 1
			#if nn > 1: break
			
			#profiler = PyCallGraph(output=GraphvizOutput(output_file=f'profile/svg_{example.name}_{filepath.name}.png'))
			#profiler.start()
			
			ctx = PseudoContext(f'Context("{str(filepath)}")')
			rnd = HTMLRenderModel()
			view = PseudoView()
			
			if filepath.suffix == '.html':
				mime = 'text/html'
			else:
				mime = 'application/xhtml+xml'

			document = rnd.create_document(filepath.read_bytes(), mime)
			l = list(rnd.scan_document_links(document))
			print(l)
			
			rnd.tree = document
			rnd.draw_image(view, document, ctx, (0, 0, 1024, 768))
				
			#profiler.done()


