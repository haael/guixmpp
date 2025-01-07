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


def once(old_method):
	def new_method(self, *args):
		if getattr(self, '__once_' + old_method.__name__, True):
			setattr(self, '__once_' + old_method.__name__, False)
			return old_method(self, *args)
	new_method.__name__ = old_method.__name__
	return new_method


class Word:
	"A single word of HTML text."
	
	def __init__(self, text, style):
		self.text = text
		self.style = style
	
	@once
	def calculate_dimensions(self, ctx, view, model, em_size):
		self.em_size = self.parent_em_size = em_size
		
		font_variant_attr = self.style['font-variant']
		if font_variant_attr == 'normal':
			self.font_variant = cairo.FONT_SLANT_NORMAL
		elif font_variant_attr == 'italic':
			self.font_variant = cairo.FONT_SLANT_ITALIC
		elif font_variant_attr == 'oblique':
			self.font_variant = cairo.FONT_SLANT_OBLIQUE
		else:
			print("unsupported font variant", font_variant_attr)
			self.font_variant = cairo.FONT_SLANT_NORMAL
		
		font_weight_attr = self.style['font-weight']
		if font_weight_attr == 'normal':
			self.font_weight = cairo.FONT_WEIGHT_NORMAL
		elif font_weight_attr in ['bold', 'bolder']:
			self.font_weight = cairo.FONT_WEIGHT_BOLD
		else:
			print("unsupported font weight", font_weight_attr)
			self.font_weight = cairo.FONT_WEIGHT_NORMAL
		
		ctx.select_font_face(self.style['font-family'], self.font_variant, self.font_weight)
		
		self.font_size = em_size # model.units(view, self.style['font-size'], percentage=em_size, em_size=em_size)
		
		ctx.set_font_size(self.font_size)
		
		text_extents = ctx.text_extents(self.text)
		font_extents = ctx.font_extents()
		
		self.content_width = text_extents.width
		self.content_height = text_extents.height
		
		self.width_request = text_extents.x_advance
		self.height_request = font_extents[0] + font_extents[1]
		
		self.baseline_request = font_extents[0]
	
	def calculate_positions(self, ctx, view, model):
		self.baseline = self.height - self.height_request + self.baseline_request
	
	def print_tree(self, level=0):
		print((" " * level) + repr(self.text))
	
	def render(self, ctx):
		color = self.style['color']
		if color is None:
			return
		elif len(color) == 3:
			ctx.set_source_rgb(*color)
		elif len(color) == 4:
			ctx.set_source_rgba(*color)
		else:
			raise ValueError
		ctx.move_to(self.x, self.y + self.baseline)
		ctx.select_font_face(self.style['font-family'], self.font_variant, self.font_weight)
		ctx.set_font_size(self.font_size)
		ctx.text_path(self.text)
		ctx.fill()


class InlineBlockElement:
	"Inline block element, like <img/>."
	
	def __init__(self, tag, elements, style):
		self.tag = tag
		self.elements = elements
		self.style = style
	
	@once
	def calculate_dimensions(self, ctx, view, model, em_size):
		self.em_size = self.parent_em_size = em_size
		self.width_request = self.content_width = 200
		self.height_request = self.content_height = 103 # FIXME
	
	def calculate_positions(self, ctx, view, model):
		pass
	
	def print_tree(self, level=0):
		print((" " * level) + "INLINE-BLOCK: " + self.tag)
		for element in self.elements:
			element.print_tree(level=level+1)
	
	def render(self, ctx):
		ctx.save()
		ctx.translate(self.x, self.y)
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.set_source_rgb(0, 0, 0)
		ctx.stroke()
		ctx.move_to(self.width / 4, self.height / 2)
		ctx.text_path(self.tag)
		ctx.fill()
		ctx.restore()


class InlineElement:
	"Inline element, like <span/>. May contain `Word`s, `InlineBlockElement`s and other `InlineElement`s."
	
	def __init__(self, tag, elements, style):
		for attr in ['word-spacing']:
			if attr not in style:
				raise ValueError(f"Required style attribute missing: {attr}.")
		if any(_element is None for _element in elements):
			raise ValueError("All elements must be non-null.")
		self.tag = tag
		self.elements = elements
		self.style = style
	
	@once
	def calculate_dimensions(self, ctx, view, model, em_size):
		self.parent_em_size = em_size
		if self.style['font-size']:
			em_size = self.em_size = model.units(view, self.style['font-size'], em_size=em_size, percentage=em_size)
		else:
			self.em_size = em_size
		
		for element in self.elements:
			element.calculate_dimensions(ctx, view, model, em_size)
		
		self.word_spacing = model.units(view, self.style['word-spacing'], em_size=em_size)
		
		self.content_width = sum(_element.width_request for _element in self.elements) if self.elements else 0
		self.content_height = max(_element.height_request for _element in self.elements) if self.elements else 0
		
		self.width_request = self.content_width + max(len(self.elements) - 1, 0) * self.word_spacing
		self.baseline_request = max(_element.baseline_request for _element in self.elements if hasattr(_element, 'baseline_request')) if any(hasattr(_element, 'baseline_request') for _element in self.elements) else 0
		
		height_request_word = (max(_element.height_request - _element.baseline_request for _element in self.elements if hasattr(_element, 'baseline_request')) if any(hasattr(_element, 'baseline_request') for _element in self.elements) else 0) + self.baseline_request
		height_request_block_inline = max(_element.height_request for _element in self.elements if not hasattr(_element, 'baseline_request')) if any(not hasattr(_element, 'baseline_request') for _element in self.elements) else 0
		self.height_request = max(height_request_word, height_request_block_inline)
	
	def calculate_positions(self, ctx, view, model):
		self.baseline = self.height - self.height_request + self.baseline_request
		
		offset = 0
		element = None
		for element in self.elements:
			element.width = element.width_request
			element.height = element.height_request
			element.x = offset
			if hasattr(element, 'baseline'):
				element.y = self.baseline - element.baseline
			else:
				element.y = 0
			element.space_after = self.word_spacing
			element.calculate_positions(ctx, view, model)
			offset += element.width + element.space_after
		if element is not None:
			del element.space_after
	
	def block_elements(self):
		for element in self.elements:
			if hasattr(element, 'block_elements'):
				for subelement in element.block_elements():
					if not hasattr(subelement, 'space_after') and hasattr(element, 'space_after'):
						subelement.space_after = element.space_after
					assert hasattr(subelement, 'width')
					yield subelement
			else:
				yield element
	
	def print_tree(self, level=0):
		print((" " * level) + "INLINE: " + self.tag)
		for element in self.elements:
			element.print_tree(level=level+1)


class Line:
	"A single line of text. Contains `Word`s and `InlineBlockElement`s extracted from `InlineElement`s."
	
	def __init__(self, elements, style):
		self.elements = elements
		self.style = style
	
	@once
	def calculate_dimensions(self, ctx, view, model, em_size):
		self.parent_em_size = self.em_size = em_size
		
		self.content_width = sum(_element.width_request for _element in self.elements)
		self.content_height = max(_element.height_request for _element in self.elements)
		
		self.width_request = sum(_element.width_request + (_element.space_after if hasattr(_element, 'space_after') else 0) for _element in self.elements) - (self.elements[-1].space_after if self.elements and hasattr(self.elements[-1], 'space_after') else 0)
		self.baseline_request = max(_element.baseline_request for _element in self.elements if hasattr(_element, 'baseline_request')) if any(hasattr(_element, 'baseline_request') for _element in self.elements) else 0
		
		height_request_word = (max(_element.height_request - _element.baseline_request for _element in self.elements if hasattr(_element, 'baseline_request')) if any(hasattr(_element, 'baseline_request') for _element in self.elements) else 0) + self.baseline_request
		height_request_block_inline = max(_element.height_request for _element in self.elements if not hasattr(_element, 'baseline_request')) if any(not hasattr(_element, 'baseline_request') for _element in self.elements) else 0
		self.height_request = max(height_request_word, height_request_block_inline)
		
		self.word_spacing = model.units(view, self.style['word-spacing'], em_size=em_size)
	
	def calculate_positions(self, ctx, view, model):
		self.baseline = self.height - self.height_request + self.baseline_request
		
		if self.style['text-align'] == 'left':
			word_spacing = self.word_spacing
			offset = 0
		elif self.style['text-align'] == 'right':
			word_spacing = self.word_spacing
			offset = self.width - self.content_width
		elif self.style['text-align'] == 'center':
			word_spacing = self.word_spacing
			offset = (self.width - self.content_width) / 2
		elif self.style['text-align'] == 'justify':
			word_spacing = (self.width - self.content_width) / max(len(self.elements) - 1, 1)
			offset = 0
		else:
			raise NotImplementedError
		
		for element in self.elements:
			element.width = element.width_request
			element.height = element.height_request
			element.x = offset
			if hasattr(element, 'baseline'):
				element.y = self.baseline - element.baseline
			else:
				element.y = 0
			element.calculate_positions(ctx, view, model)
			offset += element.width + word_spacing
	
	def print_tree(self, level=0):
		print((" " * level) + "LINE")
		for element in self.elements:
			element.print_tree(level=level+1)
	
	def render(self, ctx):
		ctx.save()
		ctx.translate(self.x, self.y)
		for element in self.elements:
			element.render(ctx)
		#ctx.rectangle(0, 0, self.width, self.height)
		#ctx.set_source_rgb(0, 0, 1)
		#ctx.stroke()
		ctx.restore()


class BlockLinesElement:
	"A block element that contains only `Line`s of text (or inline block elements)."
	
	def __init__(self, tag, elements, style):
		for attr in ['line-height']:
			if attr not in style:
				raise ValueError(f"Required style attribute missing: {attr}.")
		
		self.tag = tag
		self.elements = elements
		self.style = style
	
	@once
	def calculate_dimensions(self, ctx, view, model, em_size):
		self.parent_em_size = em_size

		if self.style['line-height']:
			self.line_height = model.units(view, self.style['line-height'], em_size=em_size, percentage=em_size)
		else:
			self.line_height = em_size
		
		if self.style['font-size']:
			em_size = self.em_size = model.units(view, self.style['font-size'], em_size=em_size, percentage=em_size)
		else:
			self.em_size = em_size
		
		style = dict(self.style)
		style['font-size'] = None
		self.inline = InlineElement(self.tag, self.elements, style)
		self.inline.calculate_dimensions(ctx, view, model, em_size)
		self.content_width = self.inline.width_request
		self.content_height = self.inline.height_request
		
		self.padding_left = model.units(view, self.style['padding-left'], em_size=em_size)
		self.padding_right = model.units(view, self.style['padding-right'], em_size=em_size)
		self.padding_top = model.units(view, self.style['padding-top'], em_size=em_size)
		self.padding_bottom = model.units(view, self.style['padding-bottom'], em_size=em_size)
		
		self.width_request = self.content_width + self.padding_left + self.padding_right
		self.height_request = self.content_height + self.padding_top + self.padding_bottom
	
	def calculate_positions(self, ctx, view, model):
		assert self.line_height is not None
		
		self.inline.width = self.inline.width_request
		self.inline.height = self.inline.height_request
		self.inline.x = 0
		self.inline.y = 0
		self.inline.calculate_positions(ctx, view, model)
		
		self.lines = []
		elements = []
		offset = None
		for element in self.inline.block_elements():
			if offset is None: offset = self.inline.elements[0].x
			if elements and element.x + element.width - offset > self.width - self.padding_left - self.padding_right:
				line = Line(elements, self.inline.style)
				line.calculate_dimensions(ctx, view, model, self.parent_em_size)
				self.lines.append(line)
				elements = []
				offset = element.x
			elements.append(element)
		if elements:
			line = Line(elements, self.inline.style)
			line.calculate_dimensions(ctx, view, model, self.parent_em_size)
			self.lines.append(line)
		
		offset = self.padding_top
		for line in self.lines:
			line.width = self.width - self.padding_left - self.padding_right
			line.height = line.height_request
			line.x = self.padding_right
			line.y = offset
			line.calculate_positions(ctx, view, model)
			assert line.height is not None
			offset += max(line.height, self.line_height)
		
		self.broken_height = offset + self.padding_bottom
	
	def print_tree(self, level=0):
		print((" " * level) + "BLOCK-LINES: " + self.tag)
		for element in self.elements:
			element.print_tree(level=level+1)
	
	def render(self, ctx):
		ctx.save()
		ctx.translate(self.x, self.y)
		for line in self.lines:
			line.render(ctx)
		
		#ctx.rectangle(self.padding_left, self.padding_top, self.width - self.padding_left - self.padding_right, self.height - self.padding_top - self.padding_bottom)
		#ctx.set_source_rgb(0.5, 0, 1)
		#ctx.stroke()
		
		ctx.restore()


class BlockElement:
	"A block element that may contain `BlockLineElement`s and other `BlockElement`s."
	
	def __init__(self, tag, elements, style):
		self.tag = tag
		self.elements = elements
		self.style = style
	
	@once
	def calculate_dimensions(self, ctx, view, model, em_size):
		self.parent_em_size = em_size
		if self.style['font-size']:
			self.em_size = em_size = model.units(view, self.style['font-size'], em_size=em_size, percentage=em_size)
		else:
			self.em_size = em_size
		
		for element in self.elements:
			element.calculate_dimensions(ctx, view, model, em_size)
		
		self.content_width = max(_element.width_request for _element in self.elements) if self.elements else 0
		self.content_height = sum(_element.height_request for _element in self.elements) if self.elements else 0
		
		self.padding_left = model.units(view, self.style['padding-left'], em_size=em_size)
		self.padding_right = model.units(view, self.style['padding-right'], em_size=em_size)
		self.padding_top = model.units(view, self.style['padding-top'], em_size=em_size)
		self.padding_bottom = model.units(view, self.style['padding-bottom'], em_size=em_size)
		
		self.width_request = self.content_width + self.padding_left + self.padding_right
		self.height_request = self.content_height + self.padding_top + self.padding_bottom
	
	def calculate_positions(self, ctx, view, model):
		offset = self.padding_top
		for element in self.elements:
			element.width = self.width - self.padding_left - self.padding_right
			element.x = self.padding_left
			element.y = offset
			element.calculate_positions(ctx, view, model)
			element.height = element.broken_height
			offset += element.broken_height
		
		self.broken_height = offset + self.padding_bottom
	
	def print_tree(self, level=0):
		print((" " * level) + "BLOCK: " + self.tag)
		for element in self.elements:
			element.print_tree(level=level+1)
	
	def render(self, ctx):
		ctx.save()
		ctx.translate(self.x, self.y)
		for element in self.elements:
			element.render(ctx)
		
		#ctx.rectangle(0, 0, self.width, self.height)
		#ctx.set_source_rgb(0, 0, 1)
		#ctx.stroke()
		
		ctx.restore()


class HTMLRender:
	xmlns_xml = XMLFormat.xmlns_xml
	xmlns_xlink = XMLFormat.xmlns_xlink
	
	xmlns_html = 'http://www.w3.org/1999/xhtml'
	xmlns_html2 = 'http://www.w3.org/2002/06/xhtml2'
	
	__whitespace_chars = ("\n", "\r", "\t", "\xA0", " ")
	
	def __init__(self, *args, **kwargs):
		self.__css_matcher = WeakKeyDictionary()
	
	def create_document(self, data, mime_type):
		if mime_type == 'application/xhtml' or mime_type == 'application/xhtml+xml' or mime_type == 'text/html':
			if mime_type == 'text/html':
				document = self.create_document(data, 'text/x-html-tag-soup')
				document.getroot().attrib['xmlns:xlink'] = self.xmlns_xlink
			else:
				document = self.create_document(data, 'application/xml')
			
			if document.getroot().tag == 'html': # document without namespace
				try:
					del document.getroot().attrib['xmlns'] # workaround: lxml sets xmlns twice
				except KeyError:
					pass
				document = self.create_document(document.to_bytes(), 'application/xml')
			
			if document.getroot().tag == 'html': # still without namespace
				document.getroot().attrib['xmlns'] = self.xmlns_html
				document = self.create_document(document.to_bytes(), 'application/xml')
			
			assert document.getroot().tag.startswith('{') # the document has namespace
			
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
				yield 'chrome:/html.css' # reset stylesheet
				yield from document.scan_stylesheets()
				#yield from self.__xlink_hrefs(document)
				yield from self.__data_internal_links(self.__style_attrs(document))
				yield from self.__data_internal_links(self.__style_tags(document))
				yield from self.__style_links(document)
				#yield from self.__script_tags(document)
			return links()
		else:
			return NotImplemented
	
	'''
	def __xlink_hrefs(self, document):
		xmlns_html = self.__xmlns(document)
		for linkedtag in chain(document.findall(f'.//*[@href]'), document.findall(f'.//*[@{{{self.xmlns_xlink}}}href]')):
			ns, tag = linkedtag.tag.split('}')
			ns = ns[1:]
			
			if ns not in [self.xmlns_html, self.xmlns_html2]:
				continue
			elif tag in ['a', 'link']:
				continue
			
			try:
				href = linkedtag.attrib[f'{{{self.xmlns_xlink}}}href']
			except KeyError:
				href = linkedtag.attrib['href']
			
			yield href
	'''
	
	def __data_internal_links(self, urls):
		"Recursively examine provided urls for internal urls they may reference."
		
		for url in urls:
			yield url
			if url.startswith('data:'):
				try:
					doc = self.get_document(url)
				except DocumentNotFound: # document may have been part-loaded
					pass # TODO: warning
				else:
					yield from self.__data_internal_links(self.scan_document_links(doc))
	
	def __style_attrs(self, document):
		"Yield all style='...' attributes as 'data:' urls."
		
		if 'style' in document.getroot().attrib:
			style = '* {' + document.getroot().attrib['style'] + '}'
			yield 'data:text/css,' + url_quote(style)
		
		for styledtag in document.findall('.//*[@style]'):
			#print(styledtag.tag, styledtag.attrib)
			style = '* {' + styledtag.attrib['style'] + '}'
			yield 'data:text/css,' + url_quote(style)
	
	def __style_links(self, document):
		"Yield all <link rel='stylesheet' href='...'> urls."
		
		xmlns_html = self.__xmlns(document)
		for linktag in document.findall(f'.//{{{xmlns_html}}}link[@rel="stylesheet"]'):
			yield linktag.attrib['href']
	
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
		
		if hasattr(document, 'getroot'): # render whole HTML document
			node = document.getroot()
		else: # render one HTML tag
			node = document
			document = document.getroottree()
		
		em_size_attr = self.__get_attribute(view, document, node, None, 'font-size', '15')
		em_size = self.units(view, em_size_attr)
		
		if not hasattr(document, '_HTMLRender__tree'):
			tree = self.__create_box(view, document, node, None)
			if isinstance(tree, Word) or isinstance(tree, InlineElement) or isinstance(tree, InlineBlockElement):
				tree = BlockLinesElement('--lines', [tree], tree.style)
			tree.calculate_dimensions(ctx, view, self, em_size)
			document.__tree = tree
		else:
			tree = document.__tree
		
		tree.x, tree.y, tree.width, tree.height = box
		tree.calculate_positions(ctx, view, self)
		
		ctx.save()
		ctx.rectangle(*box)
		ctx.clip()
		tree.render(ctx)
		ctx.restore()
	
	def poke_image(self, view, document, ctx, box, px, py):
		if not self.is_html_document(document):
			return NotImplemented
		
		xmlns_html = self.__xmlns(document)
		
		if hasattr(document, 'getroot'):
			node = document.getroot()
		else:
			node = document
			document = document.getroottree()
		
		#return self.__render_tag(view, document, ctx, box, node, em_size, (px, py))
		return []
	
	def __create_box(self, view, document, element, pseudoelement):
		if not isinstance(element.tag, str):
			return None
		namespace, tag = element.tag.split('}')
		namespace = namespace[1:]
		
		if namespace not in [self.xmlns_html, self.xmlns_html2]:
			#print("wrong namespace", namespace)
			return None
		if tag in ['script', 'head']:
			return None
		
		style = {}
		
		#font = self.__get_attribute(view, document, element, pseudoelement, 'font', None)
		style['font-size'] = self.__get_attribute(view, document, element, pseudoelement, 'font-size', None)
		style['line-height'] = self.__get_attribute(view, document, element, pseudoelement, 'line-height', style['font-size'])
		
		style['font-style'] = self.__get_attribute(view, document, element, pseudoelement, 'font-style', 'normal')
		style['font-variant'] = self.__get_attribute(view, document, element, pseudoelement, 'font-variant', 'normal')
		style['font-weight'] = self.__get_attribute(view, document, element, pseudoelement, 'font-weight', 'normal')		
		style['font-family'] = self.__get_attribute(view, document, element, pseudoelement, 'font-family', 'serif')
		
		style['word-spacing'] = self.__get_attribute(view, document, element, pseudoelement, 'word-spacing', '0.25em')
		style['text-align'] = self.__get_attribute(view, document, element, pseudoelement, 'text-align', 'left')
		
		style['color'] = self.__apply_color(view, document, element, pseudoelement, 'color', None, 'black')
		
		padding_attr = self.__get_attribute(view, document, element, pseudoelement, 'padding', '0')
		paddings = [_attr.strip() for _attr in padding_attr.split(",") if _attr.strip()]
		if len(paddings) == 0:
			padding_left = padding_right = padding_top = padding_bottom = '0'
		elif len(paddings) == 1:
			padding_left = padding_right = padding_top = padding_bottom = paddings[0]
		elif len(paddings) == 2:
			padding_top = padding_bottom = paddings[0]
			padding_left = padding_right = paddings[1]
		elif len(paddings) == 3:
			padding_top = paddings[0]
			padding_left = padding_right = paddings[1]
			padding_bottom = paddings[2]
		elif len(paddings) == 4:
			padding_top, padding_right, padding_bottom, padding_left = paddings
		elif len(paddings) > 4:
			padding_top, padding_right, padding_bottom, padding_left = paddings[:4]
		
		style['padding-top'] = self.__get_attribute(view, document, element, pseudoelement, 'padding-top', padding_top)
		style['padding-bottom'] = self.__get_attribute(view, document, element, pseudoelement, 'padding-bottom', padding_bottom)
		style['padding-left'] = self.__get_attribute(view, document, element, pseudoelement, 'padding-left', padding_left)
		style['padding-right'] = self.__get_attribute(view, document, element, pseudoelement, 'padding-right', padding_right)
		
		'''
		border_attr = self.__get_attribute(view, document, element, pseudoelement, 'border', '0')
		borders = [_attr.strip() for _attr in border_attr.split(",") if _attr.strip()]
		if len(borders) == 0:
			border_left = border_right = border_top = border_bottom = '0'
		elif len(borders) == 1:
			border_left = border_right = border_top = border_bottom = borders[0]
		elif len(borders) == 2:
			border_top = border_bottom = borders[0]
			border_left = border_right = borders[1]
		elif len(borders) == 3:
			border_top = borders[0]
			border_left = border_right = borders[1]
			border_bottom = borders[2]
		elif len(borders) == 4:
			border_top, border_right, border_bottom, border_left = borders
		elif len(borders) > 4:
			border_top, border_right, border_bottom, border_left = borders[:4]
		
		style['border-top'] = self.__get_attribute(view, document, element, pseudoelement, 'border-top', border_top)
		style['border-bottom'] = self.__get_attribute(view, document, element, pseudoelement, 'border-bottom', border_bottom)
		style['border-left'] = self.__get_attribute(view, document, element, pseudoelement, 'border-left', border_left)
		style['border-right'] = self.__get_attribute(view, document, element, pseudoelement, 'border-right', border_right)
		'''
		
		margin_attr = self.__get_attribute(view, document, element, pseudoelement, 'margin', '0')
		margins = [_attr.strip() for _attr in margin_attr.split(",") if _attr.strip()]
		if len(margins) == 0:
			margin_left = margin_right = margin_top = margin_bottom = '0'
		elif len(margins) == 1:
			margin_left = margin_right = margin_top = margin_bottom = margins[0]
		elif len(margins) == 2:
			margin_top = margin_bottom = margins[0]
			margin_left = margin_right = margins[1]
		elif len(margins) == 3:
			margin_top = margins[0]
			margin_left = margin_right = margins[1]
			margin_bottom = margins[2]
		elif len(margins) == 4:
			margin_top, margin_right, margin_bottom, margin_left = margins
		elif len(margins) > 4:
			margin_top, margin_right, margin_bottom, margin_left = margins[:4]
		
		style['margin-top'] = self.__get_attribute(view, document, element, pseudoelement, 'margin-top', margin_top)
		style['margin-bottom'] = self.__get_attribute(view, document, element, pseudoelement, 'margin-bottom', margin_bottom)
		style['margin-left'] = self.__get_attribute(view, document, element, pseudoelement, 'margin-left', margin_left)
		style['margin-right'] = self.__get_attribute(view, document, element, pseudoelement, 'margin-right', margin_right)
		
		children = []
		
		if element.text is not None:
			for word in element.text.split(" "):
				word = word.strip()
				if word:
					children.append(Word(word, style))
		
		for child in element:
			subelement = self.__create_box(view, document, child, None)
			if subelement is not None:
				children.append(subelement)
			
			if child.tail is not None:
				for word in child.tail.split(" "):
					word = word.strip()
					if word:
						children.append(Word(word, style))
		
		block_present = any(isinstance(_subelement, BlockElement) or isinstance(_subelement, BlockLinesElement) for _subelement in children)
		inline_present = any(isinstance(_subelement, Word) or isinstance(_subelement, InlineElement) or isinstance(_subelement, InlineBlockElement) for _subelement in children)
		
		display = self.__get_attribute(view, document, element, pseudoelement, 'display', 'inline')
		assert display is not None
		
		if display == 'inline-block':
			return InlineBlockElement(tag, children, style)
		
		elif display in ['block', 'inline']:
			if not block_present and inline_present:
				if display == 'block':
					return BlockLinesElement(tag, children, style)
				elif display == 'inline':
					return InlineElement(tag, children, style)
				else:
					raise ValueError
			
			elif block_present and inline_present:
				blockelements = []
				inlineelements = []
				
				for subelement in children:
					if isinstance(subelement, Word) or isinstance(subelement, InlineElement) or isinstance(subelement, InlineBlockElement):
						inlineelements.append(subelement)
					else:
						blockelements.append(BlockLinesElement('--lines', inlineelements, style))
						inlineelements = []
						blockelements.append(subelement)
				
				if inlineelements:
					blockelements.append(BlockLinesElement('--lines', inlineelements, style))
				
				return BlockElement(tag, blockelements, style)
			
			else:
				return BlockElement(tag, children, style)
			
			return InlineElement(tag, children, style)
		
		elif display == 'list-item':
			return None
		
		elif display == 'table':
			return None
		
		elif display == 'table-cell':
			return None
		
		elif display == 'table-row':
			return None
		
		elif display == 'table-row-group':
			return None
		
		elif display == 'table-column':
			return None
		
		elif display == 'table-column-group':
			return None
		
		elif display == 'none':
			return None
		
		else:
			raise NotImplementedError(f"Display: {display}")
	
	def __apply_color(self, view, document, element, pseudoelement, color_attr, opacity_attr, default_color):
		"Set painting source to the color identified by provided parameters."
		
		color = self.__get_attribute(view, document, element, pseudoelement, color_attr, default_color).strip()
		target = element.getparent()
		while color in ('currentColor', 'inherit') and (target is not None):			
			if color == 'currentColor':
				color = self.__get_attribute(view, document, element, pseudoelement, 'color', default_color).strip()
			elif color == 'inherit':
				color = self.__get_attribute(view, document, element, pseudoelement, color_attr, default_color).strip()
			target = target.getparent()
		
		assert color != 'currentColor' and color != 'inherit'
		
		try:
			color = self.web_colors[color.lower()]
		except KeyError:
			pass
		
		try:
			if not color or color.lower() in ('none', 'transparent'):
				return False
		except AttributeError:
			pass
		
		if opacity_attr is not None:
			opacity = self.__get_attribute(view, document, element, pseudoelement, opacity_attr, None)
			if opacity == 'null':
				a = None # None means 1 (full opacity), not 0 (full transparency)
			else:
				a = parse_float(opacity)
			
			if a == 0:
				return None
		else:
			a = None
		
		#if color[:4] == 'url(' and color[-1] == ')':
		#	href = color.strip()[4:-1]
		#	if href[0] == '"' and href[-1] == '"': href = href[1:-1]
		#	return self.__apply_pattern(view, document, ctx, box, node, em_size, href)
		#	# TODO: transparency
		#else:
		#	cc = self.__parse_color(color, view, node)
		#	if cc == None:
		#		return False
		#	else:
		#		r, g, b = cc
		
		cc = self.__parse_color(color, view, element)
		if cc == None:
			return None
		else:
			r, g, b = cc
		
		try:
			if a == None:
				return (r, g, b)
			else:
				return (r, g, b, a)
		except UnboundLocalError:
			pass
	
	def __parse_color(self, color, view, node):
		if color[0] == '#' and len(color) == 4:
			r, g, b = [int(_c, 16) / 15 for _c in color[1:]]
		
		elif color[0] == '#' and len(color) == 7:
			r, g, b = [int(_c, 16) / 255 for _c in (color[1:3], color[3:5], color[5:7])]
							
		elif color[:4] == 'rgb(' and color[-1] == ')':
			r, g, b = [max(0, min(1, (parse_float(_c) / 255 if _c.strip()[-1] != '%' else parse_float(_c.strip()[:-1]) / 100))) for _c in color[4:-1].split(',')]
		
		elif color[:4] == 'hsl(' and color[-1] == ')':
			cc = color[4:-1].split(',')
			
			h = max(0, min(360, (parse_float(cc[0])))) / 360
			s = max(0, min(100, (parse_float(cc[1] if cc[1][-1] != '%' else cc[1][:-1])))) / 100
			l = max(0, min(100, (parse_float(cc[2] if cc[2][-1] != '%' else cc[2][:-1])))) / 100
			
			r, g, b = hls_to_rgb(h, l, s)
		
		else:
			self.emit_warning(view, f"Unsupported color specification: {color}.", node)
			return None
		
		return r, g, b
	
	__inherited_properties = frozenset({
		'azimuth',
		'border-collapse',
		'border-spacing',
		'caption-side',
		'color',
		'cursor',
		'direction',
		'elevation',
		'empty-cells',
		'font-family',
		'font-style',
		'font-variant',
		'font-weight',
		'font',
		'letter-spacing',
		'line-height',
		'list-style-image',
		'list-style-position',
		'list-style-type',
		'list-style',
		'orphans',
		'pitch-range',
		'pitch',
		'quotes',
		'richness',
		'speak-header',
		'speak-numeral',
		'speak-punctuation',
		'speak',
		'speech-rate',
		'stress',
		'text-align',
		'text-indent',
		'text-transform',
		'visibility',
		'voice-family',
		'volume',
		'white-space',
		'widows',
		'word-spacing'
	})
	
	def __get_attribute(self, view, document, node, pseudoelement, attr, default):
		value = self.__search_attribute(view, document, node, pseudoelement, attr)
		if value is None or value == 'initial':
			value = default		
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
		#if node.tag == '{http://www.w3.org/1999/xhtml}body':
		#	print("search_attribute", node.tag, pseudoelement, attr)
		
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
						self.__css_matcher[css] = self.create_css_matcher(view, css, None, self.__get_id, None, None, None, node.tag.split('}')[1:] if node.tag[0] == '}' else '')
					css_attrs = self.__css_matcher[css](node)
					if attr in css_attrs:
						raw_value = css_attrs[attr][0]({})
						result = view.__attr_cache[node, pseudoelement][attr] = self.eval_css_value(raw_value) # TODO: css vars
						assert isinstance(result, str)
						return result
		
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
				self.__css_matcher[stylesheet] = self.create_css_matcher(view, stylesheet, (lambda _media: self.__media_test(view, _media)), self.__get_id, self.__get_classes, (lambda _node: self.__get_pseudoclasses(view, _node)), None, self.__xmlns(document))
			css_attrs = self.__css_matcher[stylesheet](node)
			
			#if node.tag == '{http://www.w3.org/1999/xhtml}body':
			#	print("", css_attrs, stylesheet)

			#if css_attrs:
			#	print("search_attribute", node.tag, pseudoelement, attr)
			#	print("", css_attrs)
			
			#css_attrs = stylesheet.match_element(document, node, (lambda _media: self.__media_test(view, _media)), self.__get_id, self.__get_classes, (lambda _node: self.__get_pseudoclasses(view, _node)), self.__pseudoelement_test)
			if attr in css_attrs:
				value, priority = css_attrs[attr]
				if css_priority == None or priority >= css_priority:
					raw_value = value({})
					css_value = self.eval_css_value(raw_value) # TODO: css vars
					assert isinstance(css_value, str)
					css_priority = priority
		
		if css_value is not None:
			view.__attr_cache[node, pseudoelement][attr] = css_value
			return css_value
		
		if attr in self.__inherited_properties:
			if pseudoelement:
				result = self.__search_attribute(view, document, node, None, attr)
				view.__attr_cache[node, None][attr] = result
				return result
			else:
				parent = node.getparent()
				if parent is not None:
					result = self.__search_attribute(view, document, parent, None, attr)
					view.__attr_cache[node, pseudoelement][attr] = result
					return result
				else:
					return None
		else:
			return None
	
	def __stylesheets(self, document):
		myurl = self.get_document_url(document)
		
		doc = self.get_document('chrome:/html.css')
		if self.is_css_document(doc):
			yield doc
		
		for link in chain(document.scan_stylesheets(), self.__data_internal_links(self.__style_tags(document)), self.__style_links(document)):
			absurl = self.resolve_url(link, myurl)
			doc = self.get_document(absurl)
			if self.is_css_document(doc):
				yield doc


if __debug__ and __name__ == '__main__':
	from pycallgraph2 import PyCallGraph
	from pycallgraph2.output.graphviz import GraphvizOutput
	
	from pathlib import Path
	from urllib.parse import unquote as url_unquote
	
	from lxml.etree import fromstring as xml_frombytes
	
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
			self.font_size = 16
		
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
			return cairo.TextExtents(0, 0, len(txt) * self.font_size, self.font_size, len(txt) * self.font_size, 0)
		
		def font_extents(self):
			if self.print_out: print(f'{self.__name}.font_extents()')
			prop = 0.8
			return (self.font_size * prop, self.font_size * (1 - prop), self.font_size, 0, self.font_size * 2, 0) # cairo.FontExtents
		
		def set_dash(self, dashes, offset):
			if self.print_out: print(f'{self.__name}.set_dash({repr(dashes)}, {repr(offset)})')
			pass
		
		def device_to_user(self, x, y):
			if self.print_out: print(f'{self.__name}.device_to_user({x}, {y})')
			return x, y
		
		def set_font_size(self, size):
			self.font_size = size
		
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
			elif url == 'chrome:/html.css':
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
		
		def get_viewport_width(self, view):
			return 1000
		
		def get_viewport_height(self, view):
			return 500
	
	class PseudoView:
		def __init__(self):
			pass
	
	
	html_piece = xml_frombytes(b'''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>litehtml * Fast and lightweight HTML/CSS rendering engine</title>
  <!-- base xhtml4 -->
	<base href="http://www.litehtml.com/" />
	<meta name="robots" content="index, follow" />
	<link rel="canonical" href="http://www.litehtml.com/" />
	<meta http-equiv="content-language" content="en" />
	<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
	<meta http-equiv="pragma" content="cache" />
	<meta http-equiv="cache-control" content="cache" />
	<meta http-equiv="Content-Style-Type" content="text/css" />
	<meta http-equiv="Content-Script-Type" content="text/javascript" />
<!-- meta -->
	<meta name="keywords" content="launch bar,true launch bar,quick launch bar,windows,launcher,taskbar,toolbar, html,css,css3,render,engine,library,open source,free" />
	
	<meta name="abstract" content="fast and lightweight HTML/CSS open source rendering engine" />
	<meta http-equiv="last-modified" content="Sun, 16 Sep 2018 22:15:58 MSK" />
	<meta name="author" content="Yuri Kobets" />
	<meta name="copyright" content="Copyright (c) 2024 by litehtml" />
	<meta name="generator" content="MODX CMS" />
	<!--[if IE]><meta http-equiv="imagetoolbar" content="no" /><![endif]-->
<!-- Dublin Core -->
	<link rel="schema.DC" href="http://purl.org/dc/elements/1.1/" />
	<meta name="DC.contributor" content="litehtml" />
	<meta name="DC.creator" content="Yuri Kobets" />
	<meta name="DC.date" content="2018-09-16" />
	<meta name="DC.format" content="text/html" />
	<meta name="DC.identifier" content="Fast and lightweight HTML/CSS rendering engine - 1288" />
	<meta name="DC.language" content="en" />
	<meta name="DC.publisher" content="litehtml" />
	<meta name="DC.rights" content="Copyright (c) 2024 by litehtml" />
	<meta name="DC.rightsHolder" content="litehtml" />
	<meta name="DC.title" content="Fast and lightweight HTML/CSS rendering engine" />
<!-- icons/rss/css -->

<!-- end MetaX output -->
  <link rel="stylesheet" type="text/css" href="assets/templates/litehtml/style.css"/>
</head>
<body>
<div class="header">
	<div style="float:right;width:728px;height:90px">
	<script type="text/javascript"><!--
google_ad_client = "ca-pub-1229827911986752";
/* litehtml-benner */
google_ad_slot = "1947231680";
google_ad_width = 728;
google_ad_height = 90;
//-->
</script>
<script type="text/javascript"
src="http://pagead2.googlesyndication.com/pagead/show_ads.js">
</script>
	</div>
	<div class="logo">lite<strong>html</strong></div>
    <div class="slogan">fast and lightweight HTML/CSS rendering engine</div>
</div>
<div class="topmenu">
	<div class="nav">
		<ul>
		  <li class="first"><a href="http://www.litehtml.com/">Home</a></li>

<li><a href="download.html">Download</a></li>

<li><a href="wiki.html">Wiki</a></li>

<li><a href="get-the-code.html">Get the code</a></li>

<li><a href="donate.html">Donate</a></li>

		</ul>
	</div>
    <div class="search-outer">
        <div class="search">
            <div class="search-input">
                <input type="text" name="search" />
            </div>
        	<div class="go">
        		<input type="button" name="go" />
    		</div>
		</div>
	</div>
</div>
<div class="content">
<!-- BEGIN content -->
<h1>What is litehtml?</h1>
<p>litehtml is lightweight HTML/CSS rendering engine. The main goal of the litehtml library is to give the developers the easy way to show the HTML pages in theirs applications. The popular HTML engines like WebKit are too complicated for some tasks. For example, it may be too cumbersome to use WebKit to show some tooltips or pages in HTML format.</p>
<h1>What web standards are supported by litehtml?</h1>
<p>I tried to make the support of HTML5/CSS3 in the litehtml. It is far from perfect, but the most HTML/CSS features are supported. Actually the appearance of HTML elements are defined by master CSS. The source code contains the master.css file as example, but you are free to use your own css. The list of the main HTML/CSS features supported by litehtml: text formating, tables, floating elements, absolute positioning, anchors, embedded styles, CSS classes, most CSS selectors etc.</p>
<h1>What litehtml uses to draw text and images?</h1>
<p>Nothing! litehtml gives you a full freedom for using any of your favorite libraries to draw text, images and other elements. litehtml calculates the position of the HTML elements, then it calls some functions from the user implemented class to draw elements and request some imformation required for rendering. This class is very simple and the source code have some implementations of this class to show how this works.</p>
<h1>What platforms are supported by litehtml?</h1>
<p>Initially litehtml was developed for Windows and was tested hard on this platform. But litehtml does not depends of any library except STL. So it is possible to use litehtml on any platform. litehtml can be compiled on linux - you can find the example in the sources.</p>
<h1>What encodings are supported by litehtml?</h1>
<p>litehtml does not handle the encodings. litehtml works with wchar_t (Windows) or utf-8 strings. Your application have to convert the HTML page before passing it into litehtml.</p>
<h1>Where to download litehtml?</h1>
<p>Please visit <a href="https://github.com/litehtml">litehtml on GitHub</a> to download the litehtml source code.</p>
<p> </p>
<!-- END content -->
</div>
  <!-- Piwik -->
<script type="text/javascript"> 
  var _paq = _paq || [];
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  (function() {
    var u=(("https:" == document.location.protocol) ? "https" : "http") + "://piwik.tordex.com//";
    _paq.push(['setTrackerUrl', u+'piwik.php']);
    _paq.push(['setSiteId', 6]);
    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0]; g.type='text/javascript';
    g.defer=true; g.async=true; g.src=u+'piwik.js'; s.parentNode.insertBefore(g,s);
  })();

</script>
<noscript><p><img src="//piwik.tordex.com/piwik.php?idsite=1" style="border:0" alt="" /></p></noscript>
<!-- End Piwik Code -->

</body>
</html>
	''')
	
	
	
	#box = create_box(html_piece)
	#ctx = PseudoContext('ctx')
	#ctx.print_out = True
	#box.calculate_dimensions(ctx)
	#box.x = 0
	#box.y = 0
	#box.width = 1000
	#box.height = 2000
	#box.calculate_positions(ctx)
	
	#box.render(ctx)
	
	#quit()
	
	#nn = 0
	for example in Path('examples').iterdir():
		if not example.is_dir(): continue
		
		for filepath in example.iterdir():
			if filepath.suffix not in ('.html', '.xhtml'): continue
			#if filepath.name != 'simple.html': continue
			print(filepath)
			#if filepath.name != 'animated-text-fine-cravings.svg': continue
			#nn += 1
			#if nn > 1: break
			
			#profiler = PyCallGraph(output=GraphvizOutput(output_file=f'profile/svg_{example.name}_{filepath.name}.png'))
			#profiler.start()
			
			ctx = PseudoContext(f'Context("{str(filepath)}")')
			ctx.print_out = True
			rnd = HTMLRenderModel()
			view = PseudoView()
			
			if filepath.suffix == '.html':
				mime = 'text/html'
			else:
				mime = 'application/xhtml+xml'

			document = rnd.create_document(filepath.read_bytes(), mime)
			l = list(rnd.scan_document_links(document))
			assert 'chrome:/html.css' in l
			
			if filepath.name == 'simple.html':
				h1 = document.find('.//html:h1', {'html':rnd.xmlns_html})
				assert rnd._HTMLRender__get_attribute(view, document, h1, None, 'display', None) == 'block'
			
			rnd.tree = document
			rnd.draw_image(view, document, ctx, (0, 0, 1000, 800))
				
			#profiler.done()


